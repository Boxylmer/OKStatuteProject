import unittest
from pathlib import Path

from statute.statuteparser import StatuteParser


TEST_DATA_DIR = Path("test/test_data")


class TestNLP(unittest.TestCase):

    ST_21_1040_13B = """A. As used in this section: 1. "Image" includes a photograph, film, videotape, digital recording or other depiction or portrayal of an object, including a human body; 2. "Intimate parts" means the fully unclothed, partially unclothed or transparently clothed genitals, pubic area or female adult nipple; and 3. "Sexual act" means sexual intercourse including genital, anal or oral sex. B. A person commits 
                        nonconsensual dissemination of private sexual images when he or she: 1. Intentionally disseminates an image of another person who is engaged in a sexual act or whose intimate parts are exposed, in whole or in part; 2. Obtains the image under circumstances in which a reasonable person would know or understand that the image was to remain private; and 3. Disseminates the image without the effective consent of the depicted person. 
                        C. The provisions of this section shall not apply to the intentional dissemination of an image of another identifiable person who is engaged in a sexual act or whose intimate parts are exposed when: 1. The dissemination is made for the purpose of a criminal investigation that is otherwise lawful; 2. The dissemination is for the purpose of, or in connection with, the reporting of unlawful conduct; 3. The images involve voluntary exposure in public or commercial settings; or 4. The dissemination serves a lawful purpose. D. Nothing in this section shall be construed to impose liability upon the following entities solely as a result of content or information provided by another person: 1. An interactive computer service, as defined in 47 U.S.C., Section 230(f)(2); 2. A wireless service provider, as defined in Section 332(d) of the Telecommunications Act of 1996, 47 U.S.C., Section 151 et seq., Federal Communications Commission rules, and the Omnibus Budget Reconciliation Act of 1993, Pub. L. No. 103-66; or 3. A telecommunications network or broadband provider. E. A person convicted under this section is subject to the forfeiture provisions in Section 1040.54 of this title. F. Any person who violates the provisions of subsection B of this section shall, upon conviction, be guilty of a misdemeanor punishable by imprisonment in a 
                        county jail for not more than one (1) year or by a fine of not more than One Thousand Dollars ($1,000.00), or both such fine and imprisonment. G. Any person who violates or attempts to violate the provisions of subsection B of this section and who gains or attempts to gain any property or who gains or attempts to gain anything of value as a result of the nonconsensual dissemination or threatened dissemination of private sexual images 
                        shall, upon conviction, be guilty of a felony punishable by imprisonment in the custody of the Department of Corrections for not more than five (5) years. A second or subsequent violation of this subsection shall be a felony punishable by imprisonment in the custody of the Department of Corrections for not more than ten (10) years and the offender shall be required to register as a sex offender under the Sex Offenders Registration Act. H. The state shall not have the discretion to file a misdemeanor charge, pursuant to Section 234 of Title 22 of the Oklahoma Statutes, for a violation pursuant to subsection G of this section. I. The court shall have 
                        the authority to order the defendant to remove the disseminated image should the court find it is in the power of the defendant to do so. J. Nothing in this section shall prohibit the prosecution of a person pursuant to the provisions of Section 1021.2 , 1021.3 , 1024.1 , 1024.2 , or 1040.12a of this title or any other applicable statute. K. Any person who violates the provisions of subsection B of this section by disseminating three 
                        or more images within a six-month period shall, upon conviction, be guilty of a felony punishable by imprisonment in the custody of the Department of Corrections for not more than ten (10) years."""

    def setUp(self):
        self.model_dir = Path("data") / "embedding_models"
        self.db_path = Path("data") / "test_chroma_db"

    def tearDown(self):
        shutil.rmtree(self.db_path, ignore_errors=True)

    def test_model_downloaded(self):
        model_path = Path(self.model_dir) / self.model_name.replace("/", "_")
        self.assertTrue(
            model_path.exists() and model_path.is_dir(),
            "Model path should exist after download.",
        )

    def test_ingest_and_query(self):
        texts = [
            "Section A. All persons born in the United States are citizens.",
            "Section B. No person shall be denied equal protection under the law.",
            "Section C. The legislature shall enact laws for public safety.",
            "Section D. Property may not be taken for public use without compensation.",
            "Section E. The governor shall have the power to grant pardons.",
            "Section F. Every person has the right to free speech.",
            "Section G. The right to bear arms shall not be infringed.",
            "Section H. Excessive bail shall not be required.",
            "Section I. Trials shall be by an impartial jury.",
            "Section J. No law shall impair the obligation of contracts.",
            "Section K. Education shall be free and public.",
            "Section L. The state shall maintain a balanced budget.",
        ]
        rag = StatuteRAG(
            model_name=self.model_name,
            model_path=self.model_dir, 
            persist=False
        )
        rag._ingest(texts)

        query = "What rights do people have regarding free speech?"
        results = rag.query(query, top_k=3)
        self.assertTrue(len(results) > 0, "Query should return at least one result.")
        self.assertTrue(results[0][0].startswith("Section F"))

        query = "Which statute section covers censorship?"
        results = rag.query(query, top_k=3)
        self.assertTrue(results[0][0].startswith("Section F"))

        query = "Which statute section covers the act of posting bond?"
        results = rag.query(query, top_k=3)
        self.assertTrue(
            results[0][0].startswith("Section H")
            or results[1][0].startswith("Section H")
            or results[2][0].startswith("Section H")
        )

    def test_ingest_statute(self):
        rag = StatuteRAG(
            model_name=self.model_name, model_path=self.model_dir, persist=False
        )
        test_html_paths = [
            TEST_DATA_DIR / "21.2.143.html",
            TEST_DATA_DIR / "21.7.301.html",
        ]
        for path in test_html_paths:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
                example_parser = StatuteParser.from_html(html)
                rag.ingest_statute(example_parser)

        query = "What happens if I prevent a group of people from gathering together?"
        results = rag.query(query, top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("felony", results[0][0])
        self.assertEqual(results[0][1]["citation"], "21.301")


        query = "How does oklahoma law prevent someone from being attacked?"
        results = rag.query(query, top_k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][1]["citation"], "21.143")