from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.videos import router as videos_router
from .routes.upload import router as upload_router

app = FastAPI(title="MARVL Video Database API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos_router)
app.include_router(upload_router)


@app.get("/")
def root():
    return {"message": "MARVL Video Database API"}


@app.get("/meta/options")
def get_options():
    return {
        "institutions": [
            "Intermountain", "SST", "HeiChole", "Cholec80",
            "UTSW", "Stanford", "AutoLaparo",
            "Medica Sur-Cortes", "Medica Sur-Hernandez",
            "München Klinik Harlaching", "Queens University",
        ],
        "procedures": [
            "Cholecystectomy", "Appendectomy", "TEP Inguinal Hernia Repair",
            "TAPP Inguinal Hernia Repair", "Hysterectomy", "Fundoplication",
            "Umbilical Hernia", "Colectomy", "Sleeve Gastrectomy",
            "Diagnostic Lap/Port Placement", "Bilateral Salpingooophrectomy",
            "Open", "Unknown", "Other",
        ],
        "anon_status": ["anonymized", "raw", "missing"],
        "annotation_status": ["Untagged", "Annotated", "In Progress"],
        "storage_systems": ["Pasteur", "SC Cluster", "GDrive"],
    }
