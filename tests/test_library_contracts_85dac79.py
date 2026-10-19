#!/usr/bin/env python3
"""Contratos da biblioteca instalada (snapshot dev, sem rede/produção).

Verifica versão via importlib.metadata (nunca __version__), localização do
pacote e assinaturas reais de context/quick_search/scrape_urls/config.
Transportes externos substituídos/bloqueados; sem sync_config/credenciais.
Pula (skip) quando a biblioteca não está instalada no ambiente corrente
(ex.: host); passa no snapshot do container com PYTHONPATH do snapshot.
"""
import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("offline: no real network")


sys.addaudithook(deny_network)

try:
    import importlib.metadata as _md
    _HAS_LIB = True
    try:
        _DIST_VER = _md.version("gpt-researcher")
    except Exception:
        _DIST_VER = None
except Exception:
    _HAS_LIB = False
    _DIST_VER = None


@unittest.skipUnless(_HAS_LIB and _DIST_VER is not None,
                     "gpt-researcher não instalado neste ambiente (host); "
                     "contrato verificado no snapshot do container")
class LibraryContracts(unittest.TestCase):
    def test_distribution_version_and_location(self):
        import importlib.metadata as md
        import gpt_researcher
        ver = md.version("gpt-researcher")
        self.assertEqual(ver, "0.16.0", f"versão instalada: {ver}")
        loc = str(md.distribution("gpt-researcher").locate_file(""))
        self.assertIn("site-packages", loc, loc)
        self.assertTrue(Path(gpt_researcher.__file__).name == "__init__.py")
        # módulos próprios do snapshot, nunca produção, quando PYTHONPATH
        # aponta para o snapshot (verificado no runner isolado).
        import adaptive_coordinator as ac
        self.assertIn(str(ROOT), ac.__file__, ac.__file__)

    def test_gpt_researcher_signatures(self):
        from gpt_researcher import GPTResearcher
        sig = inspect.signature(GPTResearcher.__init__)
        for name in ("query", "report_type", "config_path"):
            self.assertIn(name, sig.parameters, str(sig))
        self.assertIn("quick_search", dir(GPTResearcher))
        qs = inspect.signature(GPTResearcher.quick_search)
        self.assertIn("query", qs.parameters, str(qs))
        self.assertIn("get_source_urls", dir(GPTResearcher))
        wr = inspect.signature(GPTResearcher.write_report)
        self.assertIn("custom_prompt", wr.parameters, str(wr))

    def test_scrape_and_config_signatures(self):
        from gpt_researcher.actions import web_scraping as ws
        sig = inspect.signature(ws.scrape_urls)
        params = list(sig.parameters)
        self.assertIn("urls", params, str(sig))
        self.assertIn("cfg", params, str(sig))
        from gpt_researcher.config.config import Config
        csig = inspect.signature(Config.__init__)
        self.assertIn("config_path", csig.parameters, str(csig))

    def test_adapter_channel_identified_as_site_search(self):
        # O adaptador real usa busca web restrita a site para canais
        # (github/arxiv/youtube); verificado sem rede via stub researcher.
        import gpt_researcher_integration as entry
        seen = []

        class Stub:
            context = ""

            async def conduct_research(self):
                return None

            async def quick_search(self, q):
                seen.append(q)
                return []

            cfg = object()

        sfn, _, _ = entry.build_adaptive_transports(Stub())
        sfn("q", "web")  # sweep
        sfn("gap", "github")
        self.assertTrue(any("site:github.com" in q for q in seen), str(seen))


if __name__ == "__main__":
    unittest.main(verbosity=2)
