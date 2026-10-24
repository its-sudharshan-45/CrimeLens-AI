# CrimeLens AI — Report Figures & Images (PNG)

This directory contains all the figures and diagrams required for the **CrimeLens AI Project Report**, saved in high-resolution **PNG format** and organized by chapter.

---

## 📑 Figure Index

| Figure Name | Caption | Chapter | Resolution | Description |
|---|---|---|---|---|
| [`Figure_2.1_System_Architecture_Diagram.png`](./Figure_2.1_System_Architecture_Diagram.png) | Three-Tier System Architecture | Ch. 2 | 1376×768 | React Frontend, FastAPI Backend, Supabase DB & In-Process GRU Engine |
| [`Figure_2.2_Data_Preprocessing_Pipeline.png`](./Figure_2.2_Data_Preprocessing_Pipeline.png) | Six-Stage Data Preprocessing Pipeline | Ch. 2 | 1376×768 | CSV Ingestion, Validation, Resampling, Zero-fill, Z-score Normalization & Feature Engineering |
| [`Figure_2.3_Sliding_Window_Construction.png`](./Figure_2.3_Sliding_Window_Construction.png) | Sliding Window Construction for Time-Series | Ch. 2 | 1376×768 | 30-day lookback window to 7-day multi-step horizon with chronological split |
| [`Figure_2.4_CrimeGRUForecaster_Neural_Network_Architecture.png`](./Figure_2.4_CrimeGRUForecaster_Neural_Network_Architecture.png) | CrimeGRUForecaster Architecture | Ch. 2 | 768×1376 | 2-layer stacked GRU (hidden=64), Dropout (0.2), and Linear projection head |
| [`Figure_2.5_Relative_Crime_Risk_Index_Methodology.png`](./Figure_2.5_Relative_Crime_Risk_Index_Methodology.png) | Relative Crime Risk Index Methodology | Ch. 2 | 1376×768 | Ranking pass over 29 scopes, percentile score computation & category assignment |
| [`Figure_2.6_Use_Case_Diagram.png`](./Figure_2.6_Use_Case_Diagram.png) | UML Use Case Diagram | Ch. 2 | 1376×768 | Primary actors (Officer & Admin) and core system interaction workflows |
| [`Figure_3.1_Landing_Page_Hero.png`](./Figure_3.1_Landing_Page_Hero.png) | Landing Page — Hero Section | Ch. 3 | 1909×974 | Main landing page hero showcasing value proposition and navigation |
| [`Figure_3.2_Landing_Page_Features.png`](./Figure_3.2_Landing_Page_Features.png) | Landing Page — Core Modules & Features | Ch. 3 | 1909×974 | Feature highlights, AI risk forecasting description, and technical specs |
| [`Figure_3.3_Authentication_Login_Screen.png`](./Figure_3.3_Authentication_Login_Screen.png) | User Authentication — Sign In | Ch. 3 | 1909×974 | Secure login page with Supabase authentication |
| [`Figure_3.4_User_Registration_Screen.png`](./Figure_3.4_User_Registration_Screen.png) | User Registration — Sign Up | Ch. 3 | 1909×974 | New user registration form with validation feedback |
| [`Figure_3.5_Dashboard_Initial_Overview.png`](./Figure_3.5_Dashboard_Initial_Overview.png) | Dashboard — Jurisdiction Selection | Ch. 3 | 1909×974 | Initial state with State/District dropdowns and system status badge |
| [`Figure_3.6_Delhi_Crime_Risk_Prediction_and_Forecast.png`](./Figure_3.6_Delhi_Crime_Risk_Prediction_and_Forecast.png) | Risk Prediction & 7-Day Forecast — Delhi | Ch. 3 | 1909×974 | Live output: Relative Risk Gauge (High Risk 100%), Metrics & 7-day forecast cards |
| [`Figure_3.7_Mumbai_Crime_Risk_Prediction_and_Forecast.png`](./Figure_3.7_Mumbai_Crime_Risk_Prediction_and_Forecast.png) | Risk Prediction & 7-Day Forecast — Mumbai | Ch. 3 | 1909×974 | Live output: Relative Risk Gauge, Metrics & 7-day forecast cards for Mumbai City |
| [`Figure_3.8_FastAPI_Interactive_Swagger_Documentation.png`](./Figure_3.8_FastAPI_Interactive_Swagger_Documentation.png) | Backend API — FastAPI Swagger UI | Ch. 3 | 1909×974 | Interactive OpenAPI / Swagger UI documentation at `/docs` |
| [`Figure_4.1_Training_and_Validation_Loss_Curve.png`](./Figure_4.1_Training_and_Validation_Loss_Curve.png) | Model Training & Validation Loss Curve | Ch. 4 | 770×440 | Huber loss convergence across 16 epochs with early stopping |
| [`Figure_4.2_Actual_vs_Predicted_Daily_Crime_Count.png`](./Figure_4.2_Actual_vs_Predicted_Daily_Crime_Count.png) | Actual vs Predicted Daily Crime Counts | Ch. 4 | 770×440 | Test set evaluation (first 500 observations) showing model fit |
| [`Figure_4.3_Per_Horizon_Forecast_Error_MAE.png`](./Figure_4.3_Per_Horizon_Forecast_Error_MAE.png) | Per-Horizon MAE (GRU vs Baseline) | Ch. 4 | 770×440 | MAE comparison across Day +1 through Day +7 showing ~25% error reduction |
