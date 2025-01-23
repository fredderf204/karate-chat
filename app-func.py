import os, json, requests, uuid, time
from openai import AzureOpenAI
from azure.cosmos import CosmosClient
import gradio as gr
from dotenv import load_dotenv

# Setup
load_dotenv() # Load the environment variables from .env file
cosmos_db_endpoint = os.getenv("COSMOSDB_NOSQL_ACCOUNT_ENDPOINT")
cosmos_db_creds = os.getenv("COSMOSDB_NOSQL_ACCOUNT_KEY")
deployment_name = os.getenv("AZURE_OPENAI_INF_DEPLOYMENT")
db_name = os.getenv("COSMOSDB_NOSQL_DBNAME")
docs_cont_name = os.getenv("COSMOSDB_NOSQL_DOCS_CONTAINERNAME")
cache_cont_name = os.getenv("COSMOSDB_NOSQL_CACHE_CONTAINERNAME")

# Initialize the Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key= os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version= os.getenv("AZURE_OPENAI_API_VERSION")
)

# Initialize the CosmosDB Client
cosmos_client = CosmosClient(url=cosmos_db_endpoint, credential=cosmos_db_creds)

# Sample athlete data
athlete_data = {
    "Tim Bob": {"country": "australia", "category": "Junior Kumite Male -61 kg", "ranking": "10"},
    "Sally Smith": {"country": "australia", "category": "Junior Kumite Female -59 kg", "ranking": "15"},
    "Sam Greg": {"country": "australia", "category": "Cadet Kumite Male -63 kg", "ranking": "30"},
}

# Sample category data
category_data = {
    "Male Kumite -60 Kg": {1: {"name": "John Doe", "country": "USA", "points": 5820}, 2: {"name": "Jane Smith", "country": "Canada", "points": 5400}, 3: {"name": "Alice Brown", "country": "UK", "points": 5200}},
    "Female Kumite -55 Kg": {1: {"name": "Mary Johnson", "country": "USA", "points": 6000}, 2: {"name": "Sarah White", "country": "Canada", "points": 5600}, 3: {"name": "Emily Green", "country": "UK", "points": 5300}},
    "Male Kumite -67 Kg": {1: {"name": "Tom Black", "country": "USA", "points": 6200}, 2: {"name": "Mike Gray", "country": "Canada", "points": 5800}, 3: {"name": "Chris Red", "country": "UK", "points": 5400}},
}

# Helper function to create embeddings from text
def generate_embeddings(text):
    response = client.embeddings.create(input=text, model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"))
    embeddings =response.model_dump()
    time.sleep(0.5) 
    return embeddings['data'][0]['embedding']

# Helper function to check the Semantic cache
def get_cache(query_vector):
    print("checking the cache")
    db = cosmos_client.create_database_if_not_exists(
        id=db_name
    )
    container = db.get_container_client(cache_cont_name)
    # Execute the query
    results = container.query_items(
        query= '''
        SELECT TOP 1 c.completions_results
        FROM c
        WHERE VectorDistance(c.embedding,@embedding) > 0.6
        ORDER BY VectorDistance(c.embedding,@embedding)
        ''',
        parameters=[
            {"name": "@embedding", "value": query_vector},
        ],
        enable_cross_partition_query=True, populate_query_metrics=True)
    results = list(results)
    request_charge = container.client_connection.last_response_headers["x-ms-request-charge"]
    print("cache RU cost:" + request_charge)
    #print(results)
    if len(results) == 0:
        print("No cache found")
        return None
    else:
        print("Cache doc found")
        print("------------------")
        return results[0]['completions_results']

# Help Function to save a response to the Semantic cache
def save_cache(user_input, user_embeddings, completions_results):
    # Create CosmosDB Client
    db = cosmos_client.create_database_if_not_exists(
        id=db_name
    )
    container = db.get_container_client(cache_cont_name)
    
    # Create a new item
    new_item = {
        "id": str(uuid.uuid4()),
        "user_input": user_input,
        "embedding": user_embeddings,
        "completions_results": completions_results
    }
    
    # Insert the new item
    container.create_item(body=new_item)
    print("Response saved to Cache")
    print("------------------")

# Function call to get athlete data
def get_athlete_data(name):
    """Get the current rank and category for an athlete"""
    print(f"get_athlete_data called with location: {name}")  
    
    if name in athlete_data:
        athlete = athlete_data[name]
        return json.dumps({
            "name": name,
            "country": athlete["country"],
            "category": athlete["category"],
            "ranking": athlete["ranking"]
        })
    
    return json.dumps({"name": name, "error": "Athlete data not found"})    

# Function call to get category data
def get_category_data(category):
    """Get the top 3 athletes in a given category"""
    print(f"get_category_data called with category: {category}")  
    
    if category in category_data:
        athletes = category_data[category]
        return json.dumps({
            "category": category,
            "athletes": athletes
        })
    
    return json.dumps({"category": category, "error": "Category data not found"})

# Function call to query the karate index
def query_karate(search_query):
    db = cosmos_client.create_database_if_not_exists(
        id=db_name
    )
    container = db.get_container_client(docs_cont_name)

    # Turn the search query into a vector
    query_embedding = generate_embeddings(search_query)
    search_results = container.query_items(
        query='SELECT TOP @num_results c.content, VectorDistance(c.embedding,@embedding) AS SimilarityScore  FROM c ORDER BY VectorDistance(c.embedding,@embedding)',
        parameters=[
            {"name": "@embedding", "value": query_embedding}, 
            {"name": "@num_results", "value": 7} 
        ],
        enable_cross_partition_query=True)
    sources = []
    # Return the search results
    request_charge = container.client_connection.last_response_headers["x-ms-request-charge"]
    print("Doc RU cost:" + request_charge)
    for result in search_results:
        sources.append(result['content'])
    return json.dumps(sources)

def run_conversation(message, history):
    # Initial user message
    # Read the system prompt from a separate file
    def read_system_prompt(file_path):
        with open(file_path, 'r') as file:
            system_prompt = file.read()
        return system_prompt

    prompt_file_path = 'system_prompt.txt'
    system_prompt = read_system_prompt(prompt_file_path)
    
    # Define the initial messages
    history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
        ]

    # Define the functions for the model
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_athlete_data",
                "description": "gets the current rank and category for an athlete",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the athlete",
                        },
                    },
                    "required": ["name"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_category_data",
                "description": "Gets the top 3 athletes in a given category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "The name of the category",
                        },
                    },
                    "required": ["category"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_karate",
                "description": "Retrieve information about karate including terms, rules, techniques, kata and kumite.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Query string to search for karate information",
                        },
                    },
                    "required": ["search_query"],
                },
            }
        }
    ]

    # Create embeddings to search cached responses
    user_query_vect = generate_embeddings(message)

    # Check the cache for a response
    cache_response = get_cache(user_query_vect)

    # If cache is found, return the response
    if cache_response:
        return cache_response

    # API call: Ask the model to use the functions
    response = client.chat.completions.create(
        model=deployment_name,
        messages=history,
        tools=tools,
        tool_choice="auto",
    )

    # Process the model's response
    response_message = response.choices[0].message
    history.append(response_message)

    print("Model's response:")  
    print(response_message)  

    # Handle function calls
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"Function call: {function_name}")  
            print(f"Function arguments: {function_args}")  
            
            if function_name == "get_athlete_data":
                function_response = get_athlete_data(
                    name=function_args.get("name"),
                )
            elif function_name == "get_category_data":
                function_response = get_category_data(
                    category=function_args.get("category"),
                )
            elif function_name == "query_karate":
                function_response = query_karate(
                    search_query=function_args.get("search_query"),
                )
            else:
                function_response = json.dumps({"error": "Unknown function"})
            
            history.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": "<source>" + function_response + "</source>",
            })
    else:
        print("No tool calls were made by the model.")  

    # Second API call: Get the final response from the model
    final_response = client.chat.completions.create(
        model=deployment_name,
        messages=history,
    )

    # cache the response
    save_cache(message, user_query_vect, final_response.choices[0].message.content)

    # Return the final response to user
    return final_response.choices[0].message.content

# Run the conversation and print the result
#print(run_conversation())

gr.ChatInterface(
    fn=run_conversation,
    title="Karate Assistant",
    chatbot=gr.Chatbot(height=350),
    description="Ask me questions about WKF karate rules, techniques, kata or kumite.",
    theme="Ocean",
    examples=["What does yame mean?", "Who is ranked number one in the Male Kumite -60 Kg category?", "what is a jodan kick?"],
    type="messages",
    show_progress="full"
).launch()