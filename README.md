# Welcome to the karate assistant sample

This sample demonstrates how to build a sample karate chat assistant that can provide answers from structures sources (APIs) and non structured sources (knowledge bases). So you can extend your existing RAG patterns to include information from APIs when you want a more structured response.

This sample uses the following technologies;

- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/overview) for both for embeddings and inference
- [CosmosDB NoSQL API](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search) for vector indexing and search
- [Semantic Caching](https://techcommunity.microsoft.com/blog/azurearchitectureblog/optimize-azure-openai-applications-with-semantic-caching/4106867)
- [Function calling via Azure Open AI](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/function-calling)

## Pre-requisites

This sample requires the following the be in place;

- An Azure subscription
- An Azure OpenAI resource with both the embeddings and inference models you plan to use.
  - For example I used text-embedding-3-large for embeddings and gpt-4o-mini for inferencing.
- An Azure CosmosDB NoSQL API account with the Vector Search for NoSQL API enabled.
  - Please follow the instructions [here](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search#enable-the-vector-indexing-and-search-feature) to enable this feature. I can take up to 15 minutes to enable.

## Setup

1. Complete the pre-requisites
2. Clone this repository
3. Open the `karate-assistant` folder in Visual Studio Code
4. Create env file. Copy the `.env.example` file to `.env` and fill in the required values.
5. Run the docs-upload.py file. This will create the required containers, indexing policy, vector embedding policy, split the example PDF and save the embeddings to the CosmosDB.

Step 4 can take a while as it's using the [Semantic Chunker](https://python.langchain.com/docs/how_to/semantic-chunker/) provided by LangChain to create the embeddings. And in my testing they were 730 embeddings created.

## Usage

After the setup is complete you can run the `karate-assistant` by running the app-func.py file. I prefer to do this by pressing the Run and Debug button in Visual Studio Code.



Also useful information is printed during the running of this sample including;

- The number of documents uploaded
- The name of the function being called
- The function arguments
- Whether the cache was used or not
- The RU cost of the cache query and/or the vector query

## Acknowledgements

This sample is based on the following samples;

- https://github.com/microsoft/AzureDataRetrievalAugmentedGenerationSamples/blob/main/Python/CosmosDB-NoSQL_VectorSearch/CosmosDB-NoSQL-Quickstart-RAG-Chatbot.ipynb
- https://github.com/microsoft/AzureDataRetrievalAugmentedGenerationSamples/blob/main/Python/CosmosDB-NoSQL_VectorSearch/CosmosDB-NoSQL-Vector_AzureOpenAI_Tutorial.ipynb
- https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/function-calling

## Learn More

- http://aka.ms/raghack
- https://reactor.microsoft.com/en-us/reactor/events/23655/
- https://developer.microsoft.com/en-us/reactor/events/23415/

## Author

> LinkedIn [Michael Friedrich](https://www.linkedin.com/in/1michaelfriedrich/) &nbsp;&middot;&nbsp;
> GitHub [fredderf204](https://github.com/fredderf204) &nbsp;&middot;&nbsp;
> Twitter [@fredderf204](https://twitter.com/fredderf204)

## License

MIT License

Copyright (c) [2024] [Michael Friedrich]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
