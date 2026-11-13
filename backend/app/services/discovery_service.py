import logging
import time
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.campaign import Campaign
from app.models.lead import Lead, LeadSource
from app.mcp.manager import mcp_manager
from app.schemas.lead import DiscoveryResponse, DiscoveryStats, LeadResponse

logger = logging.getLogger("discovery_service")


class DiscoveryService:
    @staticmethod
    async def run_discovery_for_campaign(
        campaign_id: int,
        db: Session,
        override_limit: int = None,
    ) -> DiscoveryResponse:
        """
        Orchestrates campaign lead discovery:
        1. Validates campaign.
        2. Executes MCP search_businesses tool.
        3. Applies requirement filters (website/phone required).
        4. Detects and skips duplicates by external_id and exact name+address.
        5. Persists new leads and source citations into SQLite.
        6. Updates campaign status and returns structured statistics.
        """
        start_time = time.time()
        campaign = db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found.")

        campaign.status = "running"
        db.commit()

        limit = override_limit or campaign.max_leads or 50

        # Existing external IDs in this campaign to eliminate duplicates
        existing_stmt = select(Lead.external_id).where(Lead.campaign_id == campaign_id)
        existing_external_ids = set(db.scalars(existing_stmt).all())

        # Existing (name, address) pairs to avoid same-store duplicates
        existing_name_addr_stmt = select(Lead.business_name, Lead.address).where(
            Lead.campaign_id == campaign_id
        )
        existing_name_addrs = {
            (name.strip().lower(), (addr or "").strip().lower())
            for name, addr in db.execute(existing_name_addr_stmt).all()
            if name
        }

        try:
            # Execute through MCP Layer
            tool_args = {
                "industry": campaign.industry,
                "city": campaign.city,
                "country": campaign.country,
                "state_or_region": campaign.region,
                "limit": limit,
            }
            results = await mcp_manager.execute_tool(
                tool_name="search_businesses",
                arguments=tool_args,
                db=db,
            )

            total_found = len(results)
            new_leads_saved = 0
            duplicates_skipped = 0
            filtered_out = 0
            saved_leads: List[Lead] = []

            for item in results:
                # 1. Filter checks
                if campaign.website_required and not item.website:
                    filtered_out += 1
                    continue
                if campaign.phone_required and not item.phone:
                    filtered_out += 1
                    continue

                # 2. Duplicate detection
                if item.external_id in existing_external_ids:
                    duplicates_skipped += 1
                    continue

                norm_key = (
                    item.business_name.strip().lower(),
                    (item.address or "").strip().lower(),
                )
                if norm_key in existing_name_addrs:
                    duplicates_skipped += 1
                    continue

                # 3. Create verified lead record
                lead = Lead(
                    campaign_id=campaign.id,
                    business_name=item.business_name,
                    industry=item.industry,
                    website=item.website,
                    phone=item.phone,
                    address=item.address,
                    latitude=item.latitude,
                    longitude=item.longitude,
                    source=item.source_name,
                    external_id=item.external_id,
                    status="discovered",
                )
                db.add(lead)
                db.flush()  # populate lead.id

                # 4. Create source attribution record
                source = LeadSource(
                    lead_id=lead.id,
                    source_name=item.source_name,
                    source_url=item.source_url,
                    external_id=item.external_id,
                )
                db.add(source)

                # Track for in-batch deduplication
                existing_external_ids.add(item.external_id)
                existing_name_addrs.add(norm_key)
                saved_leads.append(lead)
                new_leads_saved += 1

                if new_leads_saved >= campaign.max_leads:
                    break

            campaign.status = "completed"
            db.commit()

            duration = round(time.time() - start_time, 2)
            stats = DiscoveryStats(
                total_found=total_found,
                new_leads_saved=new_leads_saved,
                duplicates_skipped=duplicates_skipped,
                filtered_out=filtered_out,
                execution_time_seconds=duration,
            )

            # Re-fetch leads with sources loaded
            pydantic_leads = [LeadResponse.model_validate(l) for l in saved_leads]

            return DiscoveryResponse(
                campaign_id=campaign.id,
                status=campaign.status,
                stats=stats,
                leads=pydantic_leads,
            )

        except Exception as e:
            campaign.status = "failed"
            db.commit()
            logger.error(f"Discovery failed for campaign {campaign_id}: {e}", exc_info=True)
            raise


discovery_service = DiscoveryService()
