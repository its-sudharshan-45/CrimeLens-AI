"""
backend/app/api/v1/ai.py
========================
FastAPI Router exposing Production PyTorch Deep Learning REST Endpoints.
Endpoints:
  POST /api/v1/ai/predict       — Real-time Crime Domain Classification & DB logging
  POST /api/v1/ai/forecast      — N-BEATS 7d / 30d / 90d Time-Series Forecasting
  POST /api/v1/ai/embedding     — 64-dim Dense Contrastive Vector Embedding Generation
  POST /api/v1/ai/explain       — Captum Integrated Gradients & Saliency Feature Attribution
  POST /api/v1/ai/batch-predict — Bulk CSV / JSON Batch Inference
  GET  /api/v1/ai/models        — Active Model Version & Metadata (v1.0.0)
  GET  /api/v1/ai/health        — AI Subsystem Health & Warmup Status
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.ai_service import AIService
from app.schemas.ai import (
    CrimePredictionRequest,
    CrimePredictionResponse,
    ForecastRequest,
    ForecastResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ExplainabilityRequest,
    ExplainabilityResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelHealthResponse,
    ModelMetadataResponse,
)

router = APIRouter()
ai_service = AIService()


@router.post(
    "/predict",
    response_model=CrimePredictionResponse,
    summary="Real-time Crime Domain Classification",
    description="Classifies incident sample payload into Crime Domain using PyTorch FT-Transformer & Ensemble models.",
)
async def predict_crime(
    request: CrimePredictionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        response = await ai_service.predict_crime(request, db=db)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crime prediction failed: {str(e)}",
        ) from e


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    summary="Multi-Horizon Crime Trend Forecasting",
    description="Predicts future incident volume counts (7, 30, 90 days) using PyTorch N-BEATS Forecaster.",
)
async def forecast_crime(request: ForecastRequest):
    try:
        response = await ai_service.forecast_crime(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crime forecasting failed: {str(e)}",
        ) from e


@router.post(
    "/embedding",
    response_model=EmbeddingResponse,
    summary="Generate 64-Dim Dense Vector Embedding",
    description="Generates an L2-normalized 64-dimensional dense vector embedding (E in R^64) for vector search and RAG.",
)
async def generate_embedding(request: EmbeddingRequest):
    try:
        response = await ai_service.generate_embedding(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}",
        ) from e


@router.post(
    "/explain",
    response_model=ExplainabilityResponse,
    summary="Captum Explainable AI (XAI) Attribution",
    description="Computes feature importance rankings and input sensitivity via Captum Integrated Gradients & Saliency.",
)
async def explain_prediction(request: ExplainabilityRequest):
    try:
        response = await ai_service.explain_prediction(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explainability analysis failed: {str(e)}",
        ) from e


@router.post(
    "/batch-predict",
    response_model=BatchPredictionResponse,
    summary="Bulk Batch Crime Prediction",
    description="Performs bulk inference on a list of incident records.",
)
async def batch_predict(
    request: BatchPredictionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        response = await ai_service.batch_predict(request, db=db)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}",
        ) from e


@router.get(
    "/models",
    response_model=ModelMetadataResponse,
    summary="Active Model Metadata & Version Information",
    description="Returns active model version, dataset MD5 checksum, framework details, and parameter metadata.",
)
async def get_model_metadata():
    return ai_service.get_model_metadata()


@router.get(
    "/health",
    response_model=ModelHealthResponse,
    summary="AI Subsystem Health & Probe Status",
    description="Checks PyTorch model loading status and warmup state.",
)
async def get_health_status():
    return ai_service.get_health_status()
