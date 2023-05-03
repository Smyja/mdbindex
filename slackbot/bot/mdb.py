import os
from dotenv import load_dotenv
from llama_index import GPTSimpleVectorIndex, ServiceContext
from langchain.chat_models import ChatOpenAI
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
response = index.query(
    "how to summarise text using mindsdb",
    optimizer=SentenceEmbeddingOptimizer(percentile_cutoff=0.5),
    text_qa_template=qa_prompt,
    refine_template=refine_prompt,
    service_context=service_context,
    response_mode="compact",
    similarity_cutoff=0.8,
)

if str(response) == "None":
    print("Hmm, I don't know enough to give you a confident answer yet. However, you can refer to the GPT index documentation for more information: https://gpt-index.readthedocs.io/en/latest")
else:
    yo=eval(str(response))
    answer = yo['documentation']['answer']
    follow_up_url = yo['documentation']['follow_up_url']

    # Combine them into a response
    response_text = f"{answer} Read more about this here {follow_up_url}"

    # Print the response
    print(response_text)