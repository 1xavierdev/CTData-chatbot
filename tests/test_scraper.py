import unittest

from kb import build_chunks
from scraper import TRUSTED_DOMAINS, domain_tier, reputable_links


def link(label, url):
    return {"label": label, "url": url}


class DomainTierTests(unittest.TestCase):
    def test_data_portal_is_top_priority(self):
        self.assertEqual(domain_tier("https://data.ctdata.org/dataset/grad-rates"), 0)

    def test_official_portals_match_by_subdomain(self):
        self.assertIsNotNone(domain_tier("https://public-edsight.ct.gov/"))
        self.assertIsNotNone(domain_tier("https://portal.ct.gov/"))
        self.assertIsNotNone(domain_tier("https://nces.ed.gov/"))
        self.assertIsNotNone(domain_tier("https://data.census.gov/"))
        self.assertIsNotNone(domain_tier("https://www.ctdata.org/education"))

    def test_any_gov_domain_accepted_at_lowest_priority(self):
        self.assertEqual(domain_tier("https://studentaid.gov/"), len(TRUSTED_DOMAINS))

    def test_untrusted_domains_rejected(self):
        for url in [
            "https://random-blog.example.net/post",
            "https://ctdata.org.evil-site.com/grad",
            "https://www.newspaper.com/article",
        ]:
            self.assertIsNone(domain_tier(url))


class ReputableLinksTests(unittest.TestCase):
    def test_untrusted_links_dropped(self):
        links = reputable_links([
            link("Good dataset", "https://data.ctdata.org/dataset/good"),
            link("Some blog", "https://random-blog.example.net/post"),
            link("News story", "https://www.newspaper.com/article"),
        ])
        self.assertEqual([l["url"] for l in links], ["https://data.ctdata.org/dataset/good"])

    def test_data_portal_links_always_kept_beyond_cap(self):
        links = reputable_links(
            [link(f"Dataset {i}", f"https://data.ctdata.org/dataset/{i}") for i in range(30)],
            max_links=10,
        )
        self.assertEqual(len(links), 30)

    def test_lower_priority_links_capped(self):
        links = reputable_links(
            [link(f"EdSight {i}", f"https://public-edsight.ct.gov/{i}") for i in range(30)],
            max_links=10,
        )
        self.assertEqual(len(links), 10)

    def test_data_portal_sorts_first(self):
        links = reputable_links([
            link("EdSight", "https://public-edsight.ct.gov/"),
            link("Portal dataset", "https://data.ctdata.org/dataset/x"),
        ])
        self.assertEqual(links[0]["url"], "https://data.ctdata.org/dataset/x")

    def test_duplicate_urls_kept_once(self):
        links = reputable_links([
            link("Same dataset", "https://data.ctdata.org/dataset/x"),
            link("Same dataset", "https://data.ctdata.org/dataset/x"),
        ])
        self.assertEqual(len(links), 1)


class BuildChunksTests(unittest.TestCase):
    def test_links_chunk_excludes_untrusted_sources(self):
        pages = [{
            "url": "https://www.ctdata.org/education",
            "title": "Education",
            "text": "Graduation rates",
            "links": [
                link("Official dataset", "https://data.ctdata.org/dataset/grad"),
                link("Random blog", "https://random-blog.example.net/post"),
            ],
        }]
        links_chunks = [c for c in build_chunks(pages) if c["id"].endswith("#links")]
        self.assertEqual(len(links_chunks), 1)
        self.assertIn("data.ctdata.org", links_chunks[0]["text"])
        self.assertNotIn("random-blog", links_chunks[0]["text"])


if __name__ == "__main__":
    unittest.main()
