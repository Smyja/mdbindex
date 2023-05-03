import os
import openai
from urllib.parse import urlparse
from django.shortcuts import render
from django.http import StreamingHttpResponse, HttpResponse, JsonResponse
from rest_framework.decorators import api_view


from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Create your views here.
from rest_framework.response import Response
from rest_framework import status

from .serializers import UploadedFileSerializer, AskBotSerializer
from gpt_index import GPTSimpleVectorIndex, LLMPredictor,download_loader
from langchain.chat_models import ChatOpenAI
from custom_reader import BeautifulSoupWebReader

def index(request):
    return render(request, "index.html")


@api_view(["POST"])
def upload_file(request):
    serializer = UploadedFileSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    else:
        return Response(serializer.errors, status=400)


@api_view(["POST"])
def ask_bot(request):
    """Ask the bot a question."""
    serializer = AskBotSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    prompt = serializer.validated_data["prompt"]

    loader = BeautifulSoupWebReader()
    base_url = "https://paystack.com/docs"
    parsed_url = urlparse(base_url)
    filename = parsed_url.netloc.split(".")[1]

    # save to disk
    if not os.path.exists(os.path.join(os.getcwd(), filename + ".json")):
        documents = loader.load_data(urls=[base_url], custom_hostname="readme.com")
        print(documents)
        index = GPTSimpleVectorIndex(documents, chunk_size_limit=512)
        
        index.save_to_disk(os.path.join(os.getcwd(), filename + ".json"))
        print(f"{filename}.json saved successfully!")
    else:
        print(f"{filename}.json already exists.")

        # load from disk
    index = GPTSimpleVectorIndex.load_from_disk(
        os.path.join(os.getcwd(), filename + ".json")
    )
    llm_predictor = LLMPredictor(llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo"))
    response_content = index.query(
        f"{prompt},provide a link",
        streaming=True,
    )  
    response_content = index.query(
        f"{prompt},provide a link",
        streaming=True,
    )


    # Define a generator function to iterate through the response stream
    def stream():
        for chunk in response_content.response_gen:
            yield chunk

    response = StreamingHttpResponse(stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response

@api_view(["POST"])
def generate_names(request):
    if request.method == 'POST':
        # Parse the request body and extract the prompt
        prompt = request.data.get('prompt')
        
        # Set up the OpenAI API client
        openai.api_key = OPENAI_API_KEY
        
        # Define a generator function to stream the response
        def generate_response():
            for chunk in openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                stream=True,
            ):
                content = chunk["choices"][0].get("delta", {}).get("content")
                if content is not None:
                    
                    yield content
        
        # Return a streaming response to the client
        return StreamingHttpResponse(generate_response(), content_type='text/plain')
    
    # Return a JSON error if the request method is not POST
    return JsonResponse({'error': 'Method not allowed.'}, status=405)




