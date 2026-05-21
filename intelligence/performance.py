import subprocess
import json
import os
import tempfile
import asyncio
from core.utils import setup_logger
from core.browser import BrowserManager

logger = setup_logger("intelligence.performance")

class PerformanceAnalyzer:
    @staticmethod
    async def analyze(url, browser_manager=None):
        """Analyze page performance metrics via local Lighthouse or browser timing fallbacks."""
        logger.info(f"Initiating performance analysis for {url}...")
        
        # 1. Try local Lighthouse subprocess
        lighthouse_data = await PerformanceAnalyzer._run_lighthouse(url)
        if lighthouse_data:
            return lighthouse_data
            
        # 2. Fall back to Playwright load timing if Lighthouse fails
        logger.warning("Lighthouse execution failed or timed out. Falling back to browser load timing estimates...")
        fallback_data = await PerformanceAnalyzer._run_browser_timing(url, browser_manager)
        return fallback_data

    @staticmethod
    async def _run_lighthouse(url):
        """Run Lighthouse CLI as a subprocess and parse the output JSON."""
        # Create a temp file path for the JSON report
        temp_dir = tempfile.gettempdir()
        report_path = os.path.join(temp_dir, f"lh_{os.getpid()}.json")
        
        # Command construction
        # Run lighthouse via npx to support local/global configurations
        cmd = [
            "npx", "-y", "lighthouse",
            url,
            "--output=json",
            f"--output-path={report_path}",
            "--chrome-flags=--headless --no-sandbox --disable-gpu --disable-dev-shm-usage",
            "--quiet",
            "--only-categories=performance,seo,accessibility,best-practices"
        ]
        
        try:
            logger.info(f"Running Lighthouse command: {' '.join(cmd)}")
            # Run with a 45-second timeout to prevent stalling the crawl
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=50)
                if process.returncode == 0 and os.path.exists(report_path):
                    with open(report_path, 'r') as f:
                        data = json.load(f)
                    
                    # Extract audit metrics
                    categories = data.get("categories", {})
                    audits = data.get("audits", {})
                    
                    metrics = {
                        "source": "Lighthouse",
                        "score_performance": int(categories.get("performance", {}).get("score", 0) * 100),
                        "score_accessibility": int(categories.get("accessibility", {}).get("score", 0) * 100),
                        "score_best_practices": int(categories.get("best-practices", {}).get("score", 0) * 100),
                        "score_seo": int(categories.get("seo", {}).get("score", 0) * 100),
                        "fcp_s": audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000,
                        "lcp_s": audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000,
                        "cls": audits.get("cumulative-layout-shift", {}).get("numericValue", 0),
                        "tbt_ms": audits.get("total-blocking-time", {}).get("numericValue", 0),
                        "mobile_friendly": audits.get("viewport", {}).get("score") == 1,
                        "recommendations": PerformanceAnalyzer._extract_lh_recommendations(audits)
                    }
                    return metrics
            except asyncio.TimeoutError:
                logger.warning("Lighthouse subprocess timed out.")
                try:
                    process.kill()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Lighthouse subprocess exception: {e}")
        finally:
            if os.path.exists(report_path):
                try:
                    os.remove(report_path)
                except Exception:
                    pass
        return None

    @staticmethod
    def _extract_lh_recommendations(audits):
        recs = []
        opportunities = [
            ("render-blocking-resources", "Eliminate render-blocking resources"),
            ("unused-css-rules", "Remove unused CSS"),
            ("unused-javascript", "Remove unused JavaScript"),
            ("modern-image-formats", "Serve images in modern formats"),
            ("offscreen-images", "Defer offscreen images"),
            ("uses-optimized-images", "Efficiently encode images")
        ]
        for key, label in opportunities:
            audit = audits.get(key, {})
            if audit.get("score", 1.0) < 0.9:
                recs.append(f"{label} (potential savings: {audit.get('displayValue', 'N/A')})")
        return recs[:4]

    @staticmethod
    async def _run_browser_timing(url, browser_manager):
        """Estimate load times by measuring navigation timing within Playwright."""
        bm = browser_manager or BrowserManager()
        await bm.start()
        
        # Load times estimation
        context = await bm.browser.new_context()
        page = await context.new_page()
        
        try:
            start_time = asyncio.get_event_loop().time()
            await page.goto(url, wait_until="load", timeout=20000)
            end_time = asyncio.get_event_loop().time()
            
            # Fetch browser window.performance timing metrics
            timing = await page.evaluate("window.performance.timing")
            nav_start = timing.get("navigationStart", 0)
            load_event = timing.get("loadEventEnd", 0)
            fcp_timing = timing.get("domContentLoadedEventEnd", 0)
            
            load_time_ms = load_event - nav_start if load_event > nav_start else (end_time - start_time) * 1000
            fcp_ms = fcp_timing - nav_start if fcp_timing > nav_start else load_time_ms * 0.4
            
            load_s = load_time_ms / 1000
            
            # Calculate estimated performance score
            perf_score = 100
            if load_s > 6.0:
                perf_score = 40
            elif load_s > 3.0:
                perf_score = 65
            elif load_s > 1.5:
                perf_score = 85
                
            recs = []
            if load_s > 3.0:
                recs.append(f"Optimize site assets to lower load time (currently {load_s:.2f}s).")
            if fcp_ms > 1500:
                recs.append("Optimize server response time and eliminate render-blocking elements.")
                
            return {
                "source": "Browser Timings",
                "score_performance": perf_score,
                "score_accessibility": 80, # default placeholder values
                "score_best_practices": 85,
                "score_seo": 80,
                "fcp_s": fcp_ms / 1000,
                "lcp_s": load_s,
                "cls": 0.05,
                "tbt_ms": 100,
                "mobile_friendly": True,
                "recommendations": recs
            }
        except Exception as e:
            logger.error(f"Browser-based performance timing estimate failed: {e}")
            return {
                "source": "Heuristic Estimate",
                "score_performance": 50,
                "score_accessibility": 70,
                "score_best_practices": 70,
                "score_seo": 70,
                "fcp_s": 3.0,
                "lcp_s": 6.0,
                "cls": 0.1,
                "tbt_ms": 300,
                "mobile_friendly": True,
                "recommendations": ["Optimize images and content delivery network."]
            }
        finally:
            await page.close()
            await context.close()
