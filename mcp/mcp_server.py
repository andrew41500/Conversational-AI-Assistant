from fastapi import FastAPI
from pydantic import BaseModel
import matplotlib.pyplot as plt
import io
import base64

app = FastAPI(title="MCP Chart Server")

class ChartRequest(BaseModel):
    title: str
    chart_type: str = "bar" # "bar", "line", or "scatter"
    x_data: list[str]
    y_data: list[float]
    x_label: str = ""
    y_label: str = ""

@app.post("/generate_chart")
def generate_chart(req: ChartRequest):
    plt.figure(figsize=(8, 5))
    
    if req.chart_type == "line":
        plt.plot(req.x_data, req.y_data, marker='o')
    elif req.chart_type == "scatter":
        plt.scatter(req.x_data, req.y_data)
    else:
        plt.bar(req.x_data, req.y_data)
        
    plt.title(req.title)
    if req.x_label:
        plt.xlabel(req.x_label)
    if req.y_label:
        plt.ylabel(req.y_label)
        
    plt.tight_layout()
    
    # Save to memory instead of disk
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    
    # Encode as base64 string
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return {"image_base64": encoded}
