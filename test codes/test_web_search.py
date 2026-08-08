from firecrawl import Firecrawl
from dotenv import load_dotenv
import os


load_dotenv()
firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

results = firecrawl.search(
    query="google",
    limit=3,
)
print(results)
# for result in results:
#     print(result.title, result.url)
#     print("---"*20)