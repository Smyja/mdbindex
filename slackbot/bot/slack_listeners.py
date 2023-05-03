import logging
import os
from urllib.parse import urlparse
from django.db.models import F
from dotenv import load_dotenv
from slack_bolt import App, BoltContext
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.webhook import WebhookClient
from custom_reader import BeautifulSoupWebReader

# Database models
from bot.models import SlackInstallation

# Bolt datastore implementations
from bot.slack_datastores import DjangoInstallationStore, DjangoOAuthStateStore
from llama_index import GPTSimpleVectorIndex, ServiceContext
from llama_index.prompts.prompts import QuestionAnswerPrompt, RefinePrompt
from llama_index.prompts.default_prompts import (
    DEFAULT_TEXT_QA_PROMPT_TMPL,
    DEFAULT_REFINE_PROMPT_TMPL,
)
from llama_index.output_parsers import GuardrailsOutputParser
from llama_index.llm_predictor import StructuredLLMPredictor
from llama_index.optimization.optimizer import SentenceEmbeddingOptimizer


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
logger = logging.getLogger(__name__)
client_id, client_secret, signing_secret, scopes, user_scopes = (
    os.getenv("SLACK_CLIENT_ID"),
    os.getenv("SLACK_CLIENT_SECRET"),
    os.getenv("SLACK_SIGNING_SECRET"),
    os.getenv("SLACK_SCOPES", "commands").split(","),
    os.getenv("SLACK_USER_SCOPES", "search:read").split(","),
)

app = App(
    signing_secret=signing_secret,
    oauth_settings=OAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        user_scopes=user_scopes,
        # If you want to test token rotation, enabling the following line will make it easy
        # token_rotation_expiration_minutes=1000000,
        installation_store=DjangoInstallationStore(
            client_id=client_id,
            logger=logger,
        ),
        state_store=DjangoOAuthStateStore(
            expiration_seconds=120,
            logger=logger,
        ),
    ),
)


def event_test(body, say, context: BoltContext, logger):
    logger.info(body)
  

    found_rows = list(
        SlackInstallation.objects.filter(enterprise_id=context.enterprise_id)
        .filter(team_id=context.team_id)
        .filter(incoming_webhook_url__isnull=False)
        .order_by(F("installed_at").desc())[:1]
    )
    if len(found_rows) > 0:
        webhook_url = found_rows[0].incoming_webhook_url
        logger.info(f"webhook_url: {webhook_url}")
        client = WebhookClient(webhook_url)
        client.send(text=":wave: This is a message posted using Incoming Webhook!")


# lazy listener example
def noop():
    pass

@app.event("message")
def handle_message_events(body, logger):
 logger.info(body)

@app.event("app_mention")
def mand(ack, say, body, logger):
    
    print(body)
    #check team_id
    event = body["event"]
    prompt = body["event"]["text"]
    thread_ts = event.get("thread_ts", None) or event["ts"] 
    if body["team_id"] == "T01LRR9V3J6":
        
        print(prompt)

        loader = BeautifulSoupWebReader()
        base_url = "https://paystack.com/docs"
        parsed_url = urlparse(base_url)
        filename = parsed_url.netloc.split(".")[1]

        # save to disk
        if not os.path.exists(os.path.join(os.getcwd(), filename + ".json")):
            documents = loader.load_data(urls=[base_url], custom_hostname="readme.com")
            print(documents)
            index = GPTSimpleVectorIndex(documents)
            index.save_to_disk(os.path.join(os.getcwd(), filename + ".json"))
            print(f"{filename}.json saved successfully!")
        else:
            print(f"{filename}.json already exists.")

            # load from disk
        index = GPTSimpleVectorIndex.load_from_disk(
            os.path.join(os.getcwd(), filename + ".json")
        )
        response = index.query(f"{prompt},provide a link")
    
        
        print(thread_ts)
        say("Processing your request...", thread_ts=thread_ts)
        say(text=f"{response}", thread_ts=thread_ts)
        print(response)
    elif body["team_id"] == "T01RZQL72N9":
 
        llm_predictor = StructuredLLMPredictor()
        service_context = ServiceContext.from_defaults(
            llm_predictor=llm_predictor, chunk_size_limit=512
        )


        rail_spec = """
        <rail version="0.1">

        <output>
            <object name="documentation" format="length: 2">
                <string
                    name="answer"
                    description="an answer to the question asked with a formatted code block if applicable"
                />
                <url
                    name="follow_up_url"
                    description="A source link or reference url where I can read more about this"
                    required="true"
                    format="valid-url"
                    on-fail-valid-url="filter"
                />
            </object>
        </output>

        <prompt>

        Query string here.

        @xml_prefix_prompt

        {output_schema}

        @json_suffix_prompt_v2_wo_none
        </prompt>
        </rail>
        """
        output_parser = GuardrailsOutputParser.from_rail_string(
            rail_spec, llm=llm_predictor.llm
        )
        # NOTE: we use the same output parser for both prompts, though you can choose to use different parsers
        # NOTE: here we add formatting instructions to the prompts.

        fmt_qa_tmpl = output_parser.format(DEFAULT_TEXT_QA_PROMPT_TMPL)
        fmt_refine_tmpl = output_parser.format(DEFAULT_REFINE_PROMPT_TMPL)

        qa_prompt = QuestionAnswerPrompt(fmt_qa_tmpl, output_parser=output_parser)
        refine_prompt = RefinePrompt(fmt_refine_tmpl, output_parser=output_parser)
        index = GPTSimpleVectorIndex.load_from_disk("mdb.json")
        response = index.query(f"{prompt}",
            optimizer=SentenceEmbeddingOptimizer(percentile_cutoff=0.5),
            text_qa_template=qa_prompt,
            refine_template=refine_prompt,
            service_context=service_context,
            response_mode="compact",
            similarity_cutoff=0.8
        )

        if str(response) == "None":
            
            thread_ts = event.get("thread_ts", None) or event["ts"] 
            print(thread_ts)
            say("Processing your request...", thread_ts=thread_ts)
            say(text="Hmm, I don't know enough to give you a confident answer yet. However, you can refer to the Mindsdb documentation for more information: https://docs.mindsdb.com/", thread_ts=thread_ts)
            print("Hmm, I don't know enough to give you a confident answer yet. However, you can refer to the Mindsdb documentation for more information: https://docs.mindsdb.com/")
        else:
            yo=eval(str(response))
            answer = yo['documentation']['answer']
            follow_up_url = yo['documentation']['follow_up_url']

            # Combine them into a response
            response_text = f"{answer} Read more about this here {follow_up_url}"

            # Print the response
            say("Processing your request...", thread_ts=thread_ts)
            say(text=f"{response_text}", thread_ts=thread_ts)
            print(response_text)               
    else :
        say("You are not authorised to use this bot")


