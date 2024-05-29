from fastapi import FastAPI, Path
from shared.services.grobid_service import GrobidService
import os
# docker run --rm --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.0

grobid_service = GrobidService()
app = FastAPI()


@app.get("/filename/{file_path:path}")
async def get_filename(file_path: str = Path(..., description="Path to the file")):
    """
    Returns the filename from the provided file path.
    """
    try:
        file_path = os.path.normpath(file_path)
        file_path = file_path.replace("\\", "/")
        grobid_service.process_documents(file_path)
         
        return {"Message": "Success"}
    except FileNotFoundError:
        return {"error": "File not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)