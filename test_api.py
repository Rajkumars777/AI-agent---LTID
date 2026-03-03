import asyncio
import httpx

async def test_api():
    url = "http://127.0.0.1:8000/agent/chat"
    payload = {
        "input": "create a new Book1.xlsx in Downloads, then put the value of 1,2,3,4,5 from A1 vertically and calculate the total , average and standard deviation of A1 column . And create a pp1.pptx in Downlods and input those 3 calculation into the pp1.pptx ."
    }
    
    # Use a longer timeout for the code generation step
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    asyncio.run(test_api())
