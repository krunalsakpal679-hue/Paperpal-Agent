# backend/app/agents/interpretation/csl_loader.py
"""
CSLLoader: Loads and indexes CSL (Citation Style Language) XML files.
Supports local lookup with fuzzy matching and automatic downloading from GitHub.
"""

import asyncio
import difflib
import logging
import zipfile
from pathlib import Path
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

class CSLLoader:
    """
    Manages CSL style files. Builds indices for efficient lookup and
    handles missing data by downloading from official sources.
    """

    STYLES_REPO_URL = "https://github.com/citation-style-language/styles/archive/refs/heads/master.zip"
    LOCALES_REPO_URL = "https://github.com/citation-style-language/locales/archive/refs/heads/master.zip"

    def __init__(self, csl_dir: str = "data/csl"):
        self.csl_path = Path(csl_dir).absolute()
        self.styles_path = self.csl_path / "styles"
        self.locales_path = self.csl_path / "locales"
        
        self.name_index: Dict[str, Path] = {}
        self.issn_index: Dict[str, Path] = {}
        
        # Ensure directories exist
        self.styles_path.mkdir(parents=True, exist_ok=True)
        self.locales_path.mkdir(parents=True, exist_ok=True)
        
        # Check if empty (ignoring hidden files)
        style_files = list(self.styles_path.glob("*.csl"))
        if not style_files:
            logger.info("CSL style directory is empty. Initiating download...")
            pass
        else:
            self._build_index()

    def _build_index(self):
        """Build indices from the local CSL files."""
        for csl_file in self.styles_path.glob("*.csl"):
            normalized_name = csl_file.stem.lower().replace(" ", "-")
            self.name_index[normalized_name] = csl_file

    async def ensure_data(self):
        """Download CSL data if not present."""
        if not list(self.styles_path.glob("*.csl")):
            await self._download_and_extract(self.STYLES_REPO_URL, self.styles_path)
        if not list(self.locales_path.glob("*.xml")):
            await self._download_and_extract(self.LOCALES_REPO_URL, self.locales_path)
        self._build_index()

    async def _download_and_extract(self, url: str, target_dir: Path):
        """Download a ZIP from GitHub and extract it to the target directory."""
        temp_zip = target_dir / "temp.zip"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()
                with open(temp_zip, "wb") as f:
                    f.write(response.content)
                
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
                
                subdirs = [d for d in target_dir.iterdir() if d.is_dir()]
                for subdir in subdirs:
                    for item in subdir.iterdir():
                        item.rename(target_dir / item.name)
                    subdir.rmdir()
                
                temp_zip.unlink()
                logger.info("Successfully updated CSL data from %s", url)
            except Exception as e:
                logger.error("Failed to download CSL data from %s: %s", url, e)
                if temp_zip.exists():
                    temp_zip.unlink()

    async def lookup(self, query: str) -> Optional[str]:
        """Look up a CSL style by name or ISSN."""
        if not self.name_index:
            await self.ensure_data()

        query_normalized = query.lower().strip().replace(" ", "-")
        
        if query_normalized in self.name_index:
            return self.name_index[query_normalized].read_text(encoding="utf-8")
        
        stem_matches = [name for name in self.name_index if query_normalized in name]
        if stem_matches:
            return self.name_index[stem_matches[0]].read_text(encoding="utf-8")

        matches = difflib.get_close_matches(query_normalized, list(self.name_index.keys()), n=1, cutoff=0.7)
        if matches:
            return self.name_index[matches[0]].read_text(encoding="utf-8")
            
        return None
