
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from playwright.async_api import async_playwright

try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

from core.mq.worker_base import WorkerBase

logger = logging.getLogger("ExecutorL34")

class PlaywrightPool:
    """
    Gerencia uma única instância contínua do Chromium no background.
    """
    def __init__(self, recycle_after: int = 50):
        self.playwright = None
        self.browser = None
        self.context = None
        self.pages_processed = 0
        self.recycle_after = recycle_after
        self.lock = asyncio.Lock()

    async def start(self):
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
            )
            logger.info("🎭 Chrome Engine (Playwright) Inicializado com Sucesso.")

    async def _recycle_context(self, proxy_config: Optional[Dict] = None):
        if self.context:
            await self.context.close()
        
        launch_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "device_scale_factor": 1
        }
        
        if proxy_config:
            launch_args["proxy"] = proxy_config

        self.context = await self.browser.new_context(**launch_args)
        logger.debug(f"🔄 Contexto Playwright Reciclado {'com Proxy' if proxy_config else ''}.")

    async def get_page(self, proxy_url: Optional[str] = None):
        async with self.lock:
            proxy_config = None
            if proxy_url:
                p = urlparse(proxy_url)
                proxy_config = {
                    "server": f"{p.scheme}://{p.hostname}:{p.port}",
                    "username": p.username,
                    "password": p.password
                }

            if self.browser is None:
                await self.start()
                await self._recycle_context(proxy_config)
                
            if self.pages_processed >= self.recycle_after or self.context is None or proxy_config:
                await self._recycle_context(proxy_config)
                self.pages_processed = 0

            page = await self.context.new_page()
            await page.route("**/*.{png,jpg,jpeg,webp,woff,woff2,mp4,css,gif}", lambda route: route.abort())

            if stealth_async:
                await stealth_async(page)
                
            self.pages_processed += 1
            return page

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class ExecutorL34(WorkerBase):
    """
    O Executor Bélico (Level 3-4).
    Tropa Pesada de Processamento. Consegue executar Javascript completo.
    """
    def __init__(self, redis_manager, worker_id: str = None, proxy_manager=None, 
                 concurrency: int = 5, raw_store=None, db_manager=None):
        super().__init__(
            redis_manager=redis_manager, 
            stream_name="stream:level_34", 
            group_name="workers_l34", 
            worker_id=worker_id, 
            concurrency=concurrency,
            proxy_manager=proxy_manager,
            raw_store=raw_store,
            db_manager=db_manager
        )
        self.pool = PlaywrightPool(recycle_after=50)
        self.tier = 4

    async def process_message(self, msg_id: str, data: Dict[str, Any]) -> bool:
        url = data.get("url")
        escalated_from = data.get("escalated_from", "Routing")
        
        logger.warning(f"💥 [L34 Playwright] Invadindo estrutura bloqueada em {url} (Origem: {escalated_from})")

        if not url:
            return False
            
        page = None
        try:
            domain = urlparse(url).netloc
            target_tier = self.tier
            proxy_url = None
            
            if self.proxy_manager:
                target_tier = await self.proxy_manager.resolve_tier_for_domain(domain, self.tier)
                proxy_url = self.proxy_manager.get_proxy_string_for_tier(target_tier)

            page = await self.pool.get_page(proxy_url=proxy_url)
            response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            if response is None:
                return False

            status = response.status
            
            if status in (403, 401, 429, 503) and self.proxy_manager and target_tier >= 3:
                rotator = self.proxy_manager.get_rotator_for_tier(target_tier)
                if rotator:
                    await rotator.rotate_on_block(status)
            
            html_content = await page.content()
            
            capture_id = str(uuid.uuid4())
            content_hash = self.raw_store.calculate_hash(html_content)
            
            # 1. Persistência Bruta (Raw Capture Plane)
            metadata = {
                "capture_id": capture_id,
                "mission_id": data.get("mission_id", "default"),
                "job_id": data.get("job_id", "unknown"),
                "url": url,
                "executor_level": "L34-playwright",
                "http_status": status,
                "content_type": "text/html",
                "captured_at": str(datetime.utcnow()),
                "content_hash": content_hash
            }
            
            raw_uri, meta_uri = await self.raw_store.save_artifact(
                metadata["mission_id"], capture_id, html_content, metadata
            )

            logger.info(f"💥 [L34] Sucesso: {url} | Raw: {raw_uri} | Status {status}")
            
            # 2. Emissão de Evento Desacoplado
            capture_event = data.copy()
            capture_event.update({
                "capture_id": capture_id,
                "raw_uri": raw_uri,
                "metadata_uri": meta_uri,
                "executor_level": "L34-playwright",
                "http_status": status,
                "content_hash": content_hash
            })
            
            await self.rm.client.xadd("stream:captured_raw", capture_event)
            return True

        except Exception as e:
            logger.error(f"[L34] Muro de Concreto não quebrado {url}: {e}")
            return False
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass

    async def listen(self, check_backlog: bool = True):
        await self.pool.start()
        try:
            await super().listen(check_backlog)
        finally:
            await self.pool.stop()
