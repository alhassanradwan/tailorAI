from django.db import router


@router.post("/deep-research")
async def deep_research(req: DeepResearchRequest):
    return await deep_research_service.run(req)