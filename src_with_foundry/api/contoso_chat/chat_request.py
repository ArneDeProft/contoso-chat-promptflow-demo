from dotenv import load_dotenv
load_dotenv()

from azure.cosmos import CosmosClient
from sys import argv
import os
import pathlib
from contoso_chat.product import product
from azure.identity import DefaultAzureCredential
import prompty
import prompty.azure
from prompty.tracer import trace, Tracer, console_tracer, PromptyTracer

from azure.ai.inference.models import SystemMessage, UserMessage
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.projects import AIProjectClient
from azure.ai.inference.prompts import PromptTemplate

from azure.core.settings import settings 

settings.tracing_implementation = "opentelemetry" 
from azure.ai.inference.tracing import AIInferenceInstrumentor 

# Instrument AI Inference API 

AIInferenceInstrumentor().instrument() 


#model = ChatCompletionsClient(
#    endpoint="https://ai-services-adp.services.ai.azure.com/models",
#    credential=AzureKeyCredential(os.environ["AZUREAI_ENDPOINT_KEY"]),
#    model="gpt-4o-mini"
#)

# create a project client using environment variables loaded from the .env file
project = AIProjectClient.from_connection_string(
    conn_str=os.environ["AIPROJECT_CONNECTION_STRING"], credential=DefaultAzureCredential()
)

# create a chat client we can use for testing
chat = project.inference.get_chat_completions_client()

#response = client.complete(
#    messages=[
#        SystemMessage(content="You are a helpful assistant."),
#        UserMessage(content="Explain Riemann's conjecture in 1 paragraph"),
#    ],
#    model="mistral-large"
#)

#print(response.choices[0].message.content)


# add console and json tracer:
# this only has to be done once
# at application startup
Tracer.add("console", console_tracer)
json_tracer = PromptyTracer()
Tracer.add("PromptyTracer", json_tracer.tracer)


@trace
def get_customer(customerId: str) -> str:
    try:
        url = os.environ["COSMOS_ENDPOINT"]
        client = CosmosClient(url=url, credential=DefaultAzureCredential())
        db = client.get_database_client("contoso-outdoor")
        container = db.get_container_client("customers")
        response = container.read_item(item=str(customerId), partition_key=str(customerId))
        response["orders"] = response["orders"][:2]
        print("orders: ")
        print(response["orders"])
        return response
    except Exception as e:
        print(f"Error retrieving customer: {e}")
        return None


@trace
def get_response(customerId, question, chat_history):
    print("getting customer...")
    customer = get_customer(customerId)
    print("customer complete")
    context = product.find_products(question)
    print("products complete")
    print("getting result...")

    #model_config = {
    #    "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
    #    "api_version": os.environ["AZURE_OPENAI_API_VERSION"],
    #}

   # result = prompty.execute(
   #     "chat.prompty",
   #     inputs={"question": question, "customer": customer, "documentation": context},
   #     configuration=model,
   # )


    #---
    prompty_chat_prompt = PromptTemplate.from_prompty("chat.prompty")

    system_message = prompty_chat_prompt.create_messages(documentation=context, customer=customer)

    response = chat.complete(
        model="gpt-4o-mini",
        messages= system_message,
        **prompty_chat_prompt.parameters,
    )

    return {"question": question, "answer": response.choices[0].message.content, "context": context}

if __name__ == "__main__":
    from tracing import init_tracing

    tracer = init_tracing(local_tracing=False)
    #get_response(4, "What hiking jackets would you recommend?", [])
    #get_response(argv[1], argv[2], argv[3])