from fastapi import APIRouter

from app.api.v1 import (
    approvals,
    auth,
    calibration,
    canteen,
    commercial,
    dashboard,
    devices,
    documents,
    equipment,
    finance,
    gate_passes,
    geofence,
    jobwork,
    notifications,
    otp,
    parties,
    pdfs,
    products,
    reports,
    stock,
    storage,
    sync,
    transactions,
    users,
    vehicles,
    weighments,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(geofence.router, prefix="/geofence", tags=["geofence"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["vehicles"])
api_router.include_router(gate_passes.router, prefix="/gate-passes", tags=["gate-passes"])
api_router.include_router(weighments.router, prefix="/weighments", tags=["weighments"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
api_router.include_router(stock.router, prefix="/stock", tags=["stock"])
api_router.include_router(jobwork.router, prefix="/job-work", tags=["job-work"])
api_router.include_router(otp.router, prefix="/otp", tags=["otp"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(pdfs.router, prefix="/pdfs", tags=["pdfs"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(canteen.router, prefix="/canteen", tags=["canteen"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(approvals.router, tags=["approvals"])
api_router.include_router(parties.router, tags=["parties"])
api_router.include_router(calibration.router, prefix="/calibration", tags=["calibration"])
api_router.include_router(commercial.router, prefix="/commercial", tags=["commercial"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
