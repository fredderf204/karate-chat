# Description: This script reads a PDF file, splits the text into chunks, creates embeddings for each chunk, and uploads the chunks to CosmosDB.
# Based partially on Quickstart - Build a RAG chatbot with Azure Cosmos DB NoSQL API: https://github.com/microsoft/AzureDataRetrievalAugmentedGenerationSamples/blob/main/Python/CosmosDB-NoSQL_VectorSearch/CosmosDB-NoSQL-Quickstart-RAG-Chatbot.ipynb
import json, os, time
from azure.cosmos import CosmosClient
from azure.cosmos.aio import CosmosClient as CosmosClientAsync
from azure.cosmos import PartitionKey, exceptions
from openai import AzureOpenAI
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import AzureOpenAIEmbeddings

load_dotenv()

cosmos_db_endpoint = os.getenv("COSMOSDB_NOSQL_ACCOUNT_ENDPOINT")
cosmos_db_creds = os.getenv("COSMOSDB_NOSQL_ACCOUNT_KEY")
cosmos_vector_property = "embedding"
db_name = os.getenv("COSMOSDB_NOSQL_DBNAME")
docs_cont_name = os.getenv("COSMOSDB_NOSQL_DOCS_CONTAINERNAME")
cache_cont_name = os.getenv("COSMOSDB_NOSQL_CACHE_CONTAINERNAME")

# Create AOAI Client
AOAI_client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version= os.getenv("AZURE_OPENAI_API_VERSION")
)

# Create CosmosDB Client
cosmos_client = CosmosClient(url=cosmos_db_endpoint, credential=cosmos_db_creds)

# Create database
db = cosmos_client.create_database_if_not_exists(
    id = db_name
)
properties = db.read()
print(json.dumps(properties, indent=True))

# Create the vector index policy to specify vector details
# https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search#vector-indexing-policies
indexing_policy = {
    "includedPaths": [{"path": "/*"}],
    "excludedPaths": [{"path": '/"_etag"/?', "path": "/" + cosmos_vector_property + "/*" }],
    "vectorIndexes": [{"path": "/" + cosmos_vector_property, "type": "quantizedFlat"}],
}

# Create the vector embedding policy to specify vector details
# https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search#container-vector-policies
vector_embedding_policy = {
    "vectorEmbeddings": [
        {
            "path": "/" + cosmos_vector_property,
            "dataType": "float32",
            "distanceFunction": "cosine",
            "dimensions": 1536,
        }
    ]
}

####################################################################################################################################
###### You will need to enable the vector indexing and search feature (EnableNoSQLVectorSearch) before creating the container ######
####################################################################################################################################
# https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search#enable-the-vector-indexing-and-search-feature
# Create the docs container with vector index
try:    
    container = db.create_container_if_not_exists(
                    id=docs_cont_name,
                    partition_key=PartitionKey(path='/id'),
                    indexing_policy=indexing_policy,
                    vector_embedding_policy=vector_embedding_policy)

    print('Container with id ' + docs_cont_name + ' created'.format(id))

except exceptions.CosmosResourceExistsError:
    print('A container with id ' + docs_cont_name + ' already exists'.format(id))

# Create the cache container with vector index
try:    
    container = db.create_container_if_not_exists(
                    id=cache_cont_name,
                    partition_key=PartitionKey(path='/id'),
                    default_ttl=900,
                    indexing_policy=indexing_policy,
                    vector_embedding_policy=vector_embedding_policy)

    print('Container with id ' + cache_cont_name + ' created'.format(id))

except exceptions.CosmosResourceExistsError:
    print('A container with id ' + cache_cont_name + ' already exists'.format(id))

# Helper function to create embeddings from text
def generate_embeddings(text):
    response = AOAI_client.embeddings.create(input=text, model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"))
    embeddings =response.model_dump()
    time.sleep(0.5) 
    return embeddings['data'][0]['embedding']

# open pdfs, split text create embeddings and upload to cosmosdb
loader = PyPDFLoader("./data/WKF_Kumite_Competition_Rules_2024.pdf")
pdf = loader.load()

# Embedding Client
embeddings = AzureOpenAIEmbeddings(
    azure_deployment = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    openai_api_key = os.getenv("AZURE_OPENAI_API_KEY"),
    openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
)

# Sematic Chunking - https://python.langchain.com/docs/how_to/semantic-chunker/
semantic_splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile", breakpoint_threshold_amount=0.95)

# Recursive Character Text Splitter - https://python.langchain.com/docs/concepts/text_splitters/
# Text-structured based splitting
#text_splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=50)

# Create container client
container_client = db.get_container_client(docs_cont_name)
n = 0
for page in pdf:
    chunks = semantic_splitter.split_text(page.page_content)
    #chunks = text_splitter.split_text(page.page_content)
    # Loop over chunks and upload to cosmosdb
    for chunk in chunks:
        n += 1
        doc = {}
        doc['id'] = str(n)
        doc['content'] = chunk
        doc['embedding'] = generate_embeddings(chunk)
        doc['filename'] = page.metadata['source']
        print("writing item " + doc['id'] + ' to ' + db.get_container_client(docs_cont_name).id)
        container_client.upsert_item(doc)

