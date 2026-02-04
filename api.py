"""
Main API endpoint for AgriMitra workflow
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
from workflow import AgriMitraWorkflow
import tempfile
import os

# Import buyer connect API router
from buyer_connect_api import router as buyer_connect_router

logger = logging.getLogger(__name__)

app = FastAPI(title="AgriMitra API", version="1.0.0")

# Include buyer connect API routes
app.include_router(buyer_connect_router, prefix="/api")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize workflow
workflow = AgriMitraWorkflow()


class QueryRequest(BaseModel):
    query: str
    image_path: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "AgriMitra API", "version": "1.0.0"}


@app.post("/api/query")
async def process_query(request: QueryRequest):
    """
    Process a farmer's query through the AgriMitra workflow
    
    Returns the complete workflow response with agent outputs
    """
    try:
        print("\n" + "="*80)
        print("🌾 AGRI MITRA WORKFLOW EXECUTION")
        print("="*80)
        print(f"📝 User Query: {request.query}")
        if request.image_path:
            print(f"📷 Image Path: {request.image_path}")
        print("-"*80)
        
        logger.info(f"Processing query: {request.query}")
        result = workflow.run(user_input=request.query, image_path=request.image_path)
        
        # Print workflow execution details
        print("\n📊 WORKFLOW EXECUTION SUMMARY:")
        print("-"*80)
        
        # Reasoner output
        if result.get("reasoner_output"):
            reasoner = result["reasoner_output"]
            if isinstance(reasoner, dict):
                intent = reasoner.get("intent", "Unknown")
                agents = reasoner.get("agents_to_trigger", [])
                crop = reasoner.get("crop", "None")
                print(f"🤖 Reasoner:")
                print(f"   Intent: {intent}")
                print(f"   Agents to trigger: {agents}")
                print(f"   Crop detected: {crop}")
            else:
                print(f"🤖 Reasoner output: {reasoner}")
        
        # Agent outputs
        if result.get("disease_agent_output"):
            disease = result["disease_agent_output"]
            disease_info = disease.get("disease_info", {})
            identified = disease_info.get("identified_disease") or disease_info.get("disease", "Unknown")
            print(f"🦠 Disease Agent:")
            print(f"   Identified Disease: {identified}")
            if disease.get("remedy_info"):
                print(f"   Remedy Available: Yes")
        
        if result.get("price_agent_output"):
            price = result["price_agent_output"]
            price_info = price.get("price_info", {})
            current_price = price_info.get("current_price") or price_info.get("price", "N/A")
            print(f"💰 Price Agent:")
            print(f"   Current Price: ₹{current_price}")
        
        if result.get("buyer_connect_agent_output"):
            buyer = result["buyer_connect_agent_output"]
            matched = len(buyer.get("matched_buyers", []))
            print(f"🤝 Buyer Connect Agent:")
            print(f"   Matched Buyers: {matched}")
        
        if result.get("scheme_agent_output"):
            scheme = result["scheme_agent_output"]
            schemes = len(scheme.get("schemes", []))
            print(f"🏛️  Scheme Agent:")
            print(f"   Schemes Found: {schemes}")
        
        # Final response
        if result.get("final_response"):
            print(f"\n💡 Final Response:")
            print(f"   {result['final_response'][:200]}..." if len(result['final_response']) > 200 else f"   {result['final_response']}")
        
        # Execution log
        if result.get("execution_log"):
            print(f"\n📋 Execution Log ({len(result['execution_log'])} steps):")
            for i, log_entry in enumerate(result["execution_log"], 1):
                node = log_entry.get("node", "Unknown")
                print(f"   {i}. {node}")
                if log_entry.get("error"):
                    print(f"      ❌ Error: {log_entry['error']}")
        
        print("="*80 + "\n")
        
        # Debug: Print what we're returning
        print("🔍 RETURNING RESPONSE STRUCTURE:")
        print(f"  - disease_agent_output: {bool(result.get('disease_agent_output'))}")
        print(f"  - price_agent_output: {bool(result.get('price_agent_output'))}")
        print(f"  - scheme_agent_output: {bool(result.get('scheme_agent_output'))}")
        print(f"  - buyer_connect_agent_output: {bool(result.get('buyer_connect_agent_output'))}")
        print(f"  - reasoner_output: {bool(result.get('reasoner_output'))}")
        print("="*80 + "\n")
        
        return result
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        import traceback
        print(f"\n❌ ERROR: {e}")
        print(traceback.format_exc())
        print("="*80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/upload")
async def process_query_with_image(
    query: str | None = Form(None),
    image: UploadFile | None = File(None)
):
    """
    Process a query with an uploaded image
    
    Args:
        query: Text query from the user
        image: Uploaded image file
    """
    if not query and not image:
        raise HTTPException(
            status_code=400,
            detail="Either query or image must be provided"
        )
    try:
        print("\n" + "="*80)
        print("🌾 AGRI MITRA WORKFLOW EXECUTION (WITH IMAGE)")
        print("="*80)
        print(f"📝 User Query: {query}")
        print(f"📷 Image: {image.filename} ({image.content_type})")
        print("-"*80)
        
        # Save uploaded image temporarily
        file_extension = os.path.splitext(image.filename or "image")[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await image.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        print(f"💾 Temporary image saved: {tmp_path}")
        
        logger.info(f"Processing query with image: {query}, image_path: {tmp_path}")
        result = workflow.run(user_input=query, image_path=tmp_path)
        
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
            print(f"🗑️  Temporary file deleted: {tmp_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete temporary file {tmp_path}: {cleanup_error}")
        
        # Print workflow execution details (same as text-only endpoint)
        print("\n📊 WORKFLOW EXECUTION SUMMARY:")
        print("-"*80)
        
        # Reasoner output
        if result.get("reasoner_output"):
            reasoner = result["reasoner_output"]
            if isinstance(reasoner, dict):
                intent = reasoner.get("intent", "Unknown")
                agents = reasoner.get("agents_to_trigger", [])
                crop = reasoner.get("crop", "None")
                print(f"🤖 Reasoner:")
                print(f"   Intent: {intent}")
                print(f"   Agents to trigger: {agents}")
                print(f"   Crop detected: {crop}")
        
        # Agent outputs
        if result.get("disease_agent_output"):
            disease = result["disease_agent_output"]
            disease_info = disease.get("disease_info", {})
            identified = disease_info.get("identified_disease") or disease_info.get("disease", "Unknown")
            print(f"🦠 Disease Agent:")
            print(f"   Identified Disease: {identified}")
            if disease.get("image_processing_note"):
                note = disease["image_processing_note"]
                if note.get("cnn_unavailable"):
                    print(f"   ⚠️  CNN Model: Not Available (TensorFlow required)")
                    print(f"   📝 Message: {note.get('message', 'N/A')}")
                    if note.get("fallback_to_text"):
                        print(f"   ✅ Fallback: Using text-based diagnosis")
            if disease.get("remedy_info"):
                print(f"   Remedy Available: Yes")
        
        if result.get("price_agent_output"):
            price = result["price_agent_output"]
            price_info = price.get("price_info", {})
            current_price = price_info.get("current_price") or price_info.get("price", "N/A")
            print(f"💰 Price Agent:")
            print(f"   Current Price: ₹{current_price}")
        
        print("="*80 + "\n")
        
        return result
    except Exception as e:
        logger.error(f"Error processing query with image: {e}")
        import traceback
        print(f"\n❌ ERROR: {e}")
        print(traceback.format_exc())
        print("="*80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

