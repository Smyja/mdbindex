import logging
import os
from urllib.parse import urlparse
from django.db.models import F
from dotenv import load_dotenv
from slack_bolt import App, BoltContext
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.webhook import WebhookClient
from langchain.agents import Tool
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain import OpenAI
from langchain.agents import initialize_agent

from llama_index import GPTSimpleVectorIndex

# Database models
from bot.models import SlackInstallation

# Bolt datastore implementations
from bot.slack_datastores import DjangoInstallationStore, DjangoOAuthStateStore
from llama_index import GPTSimpleVectorIndex, download_loader
from llama_index.langchain_helpers.chatgpt import ChatGPTLLMPredictor

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
    say(":wave: What's up?")

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


app.event("app_mention")(
    ack=event_test,
    lazy=[noop],
)


@app.command("/ask")
def command(ack, say, body, logger):
    ack("Processing your request...")
    prompt = body["text"]
    print(prompt)

    RemoteReader = download_loader("BeautifulSoupWebReader")
    llm_predictor = ChatGPTLLMPredictor()
    loader = RemoteReader()
    base_url = "https://docs.mono.co/docs"
    parsed_url = urlparse(base_url)
    filename = parsed_url.netloc.split(".")[1]

    # save to disk
    if not os.path.exists(os.path.join(os.getcwd(), filename + ".json")):
        documents = loader.load_data(urls=[base_url], custom_hostname="readme.com")
        index = GPTSimpleVectorIndex(documents, llm_predictor=llm_predictor)
        index.save_to_disk(os.path.join(os.getcwd(), filename + ".json"))
        print(f"{filename}.json saved successfully!")
    else:
        print(f"{filename}.json already exists.")

        # load from disk
    index = GPTSimpleVectorIndex.load_from_disk(
        os.path.join(os.getcwd(), filename + ".json")
    )
    tools = [
        Tool(
            name="GPT Index",
            func=lambda q: str(index.query(q, llm_predictor=llm_predictor)),
            description="useful for when you want to answer questions about the author. The input to this tool should be a complete english sentence.",
            return_direct=True,
        ),
    ]
    memory = ConversationBufferMemory(memory_key="chat_history")
    llm = OpenAI(temperature=0)
    agent_chain = initialize_agent(
        tools, llm, agent="conversational-react-description", memory=memory
    )
    response = agent_chain.run(input=prompt)
    say(f"Query: {prompt} \nResponse: {response}")
    print(response)
