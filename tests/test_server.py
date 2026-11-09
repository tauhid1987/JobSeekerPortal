"""Server tests: search filters and the approval email. No network, no Firebase, no real email.
Run from the project folder:   .venv\\Scripts\\python -m unittest discover -s tests -p "test_*.py"
"""
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import server, mailer, fbauth  # noqa: E402

CV = ("Software tester with 3 years of experience in manual testing, test cases, Selenium, API testing with Postman, SQL, Jira and bug reports. " * 4)


def job(i, title, loc, remote, desc, country=""):
    return dict(title=title, company=f"Co{i}", apply_url=f"https://x.test/{i}", remote=remote, location=loc,
                description=desc, tags=[], country=country, source="test", salary="", type="", posted="")


def many_us_only_and_some_open():
    """60 jobs that match the CV best but are US-only, plus worldwide remote jobs that match less well."""
    jobs = [job(i, "QA Engineer Selenium Jira", "USA", True, "qa engineer selenium sql jira postman testing " * 30 + " must be authorized to work in the US")
            for i in range(60)]
    jobs += [job(i, "Support Specialist" if i % 2 else "Test Analyst", "Worldwide", True, "customer testing role, sql basics, remote worldwide " * 10)
             for i in range(60, 360)]
    jobs += [job(i, "Chef", "Paris", False, "cook food " * 10) for i in range(120, 300)]
    return jobs


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        server._last.clear()
        self.patches = [
            mock.patch.object(fbauth, "verify_token", return_value=("uid1", {})),
            mock.patch.object(fbauth, "status", return_value="member"),
            mock.patch.object(fbauth, "log_activity", return_value={}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        mock.patch.stopall()

    def search(self, jobs, **form):
        data = {"cv": (io.BytesIO(CV.encode()), "cv.txt"), "query": "QA Engineer", "country": "Bangladesh", "scope": "both"}
        data.update(form)
        with mock.patch.object(server, "search_all", return_value=jobs):
            server._last.clear()
            return self.client.post("/api/search", data=data, headers={"Authorization": "Bearer t"}, content_type="multipart/form-data")

    def test_closed_jobs_do_not_push_out_open_ones(self):
        """The bug: 60 best matches were US-only, so after the eligibility filter nothing was left."""
        r = self.search(many_us_only_and_some_open(), eligibility="strict", min_score="20")
        self.assertEqual(r.status_code, 200, r.get_json())
        d = r.get_json()
        self.assertGreater(len(d["jobs"]), 0)
        self.assertTrue(all(j["eligible"] != "No" for j in d["jobs"]))
        self.assertGreaterEqual(d["not_eligible"], 60)

    def test_nothing_reaches_minimum_shows_closest_with_notice(self):
        jobs = [job(i, "Support Specialist", "Worldwide", True, "customer testing role remote worldwide " * 6) for i in range(30)]
        r = self.search(jobs, min_score="95")
        self.assertEqual(r.status_code, 200, r.get_json())
        d = r.get_json()
        self.assertTrue(d["notice"])
        self.assertGreater(len(d["jobs"]), 0)

    def test_all_closed_gives_a_specific_message(self):
        jobs = [job(i, "QA Engineer", "USA", False, "on site in new york, no visa sponsorship " * 5) for i in range(15)]
        r = self.search(jobs, eligibility="strict")
        self.assertEqual(r.status_code, 400)
        msg = r.get_json()["error"]
        self.assertIn("not open to Bangladesh", msg)
        self.assertIn("Show all, with status", msg)

    def test_show_all_lists_closed_jobs_with_status(self):
        jobs = [job(i, "QA Engineer", "USA", False, "on site in new york, no visa sponsorship " * 5) for i in range(15)]
        r = self.search(jobs, eligibility="all")
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(all(j["eligible"] == "No" for j in r.get_json()["jobs"]))

    def test_bad_numbers_do_not_crash(self):
        r = self.search(many_us_only_and_some_open(), min_score="abc", limit="zzz")
        self.assertEqual(r.status_code, 200, r.get_json())

    def test_feeds_returned_nothing(self):
        r = self.search([])
        self.assertEqual(r.status_code, 400)
        self.assertIn("returned nothing", r.get_json()["error"])


class EmailTests(unittest.TestCase):
    GOOD = ["a@b.co", "tauhid.islam+jobs@gmail.com", "x_y-z@mail.example.com.bd"]
    BAD = ["", "plain", "a@b", "a@@b.com", "a b@c.com", "a@b..com", "a@.com", "a@b.c", "@b.com", ".a@b.com"[:0] or "a@b.com\r\nBcc: z@z.com"]

    def test_valid_and_invalid_addresses(self):
        for a in self.GOOD:
            self.assertTrue(mailer.valid_email(a), a)
        for a in self.BAD:
            self.assertFalse(mailer.valid_email(a), repr(a))

    def test_message_has_link_and_safe_headers(self):
        with mock.patch.dict(os.environ, {"SMTP_USER": "sender@example.com", "SITE_URL": "https://site.test/"}):
            m = mailer.build_approval("user@example.com", "Rina\r\nBcc: evil@x.com <b>")
        self.assertEqual(m["To"], "user@example.com")
        self.assertNotIn("Bcc", m)
        body = m.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("https://site.test/", body)
        self.assertEqual(m["Subject"], "Your JobMatch access is approved")

    def test_refuses_bad_recipient(self):
        with self.assertRaises(ValueError):
            mailer.build_approval("not-an-email", "x")


class NotifyTests(unittest.TestCase):
    SMTP = {"SMTP_HOST": "smtp.test", "SMTP_PORT": "587", "SMTP_USER": "sender@example.com", "SMTP_PASSWORD": "pw"}

    def setUp(self):
        self.client = server.app.test_client()
        server._mailed.clear()
        self.db = {"jm/members/user12345": {"active": True, "name": "Rina"},
                   "jm/requests/user12345": {"name": "Rina", "email": "rina@example.com"}}
        self.status = "admin"
        mock.patch.object(fbauth, "verify_token", return_value=("admin1", {})).start()
        mock.patch.object(fbauth, "status", side_effect=lambda uid, tok: self.status).start()
        mock.patch.object(fbauth, "db_get", side_effect=lambda path, tok: self.db.get(path)).start()

    def tearDown(self):
        mock.patch.stopall()

    def call(self, uid="user12345"):
        return self.client.post("/api/notify-approved", json={"uid": uid}, headers={"Authorization": "Bearer t"})

    def test_admin_sends_one_email_to_the_stored_address(self):
        with mock.patch.dict(os.environ, self.SMTP), mock.patch("smtplib.SMTP") as smtp:
            r = self.call()
        self.assertEqual(r.status_code, 200, r.get_json())
        sent = smtp.return_value.__enter__.return_value.send_message.call_args[0][0]
        self.assertEqual(sent["To"], "rina@example.com")

    def test_member_cannot_trigger_email(self):
        self.status = "member"
        with mock.patch.dict(os.environ, self.SMTP), mock.patch("smtplib.SMTP") as smtp:
            r = self.call()
        self.assertEqual(r.status_code, 401)
        smtp.assert_not_called()

    def test_not_approved_yet(self):
        self.db["jm/members/user12345"] = {"active": False, "name": "Rina"}
        with mock.patch.dict(os.environ, self.SMTP), mock.patch("smtplib.SMTP") as smtp:
            r = self.call()
        self.assertEqual(r.status_code, 409)
        smtp.assert_not_called()

    def test_invalid_stored_email_is_not_mailed(self):
        self.db["jm/requests/user12345"] = {"name": "Rina", "email": "rina@nowhere"}
        with mock.patch.dict(os.environ, self.SMTP), mock.patch("smtplib.SMTP") as smtp:
            r = self.call()
        self.assertEqual(r.status_code, 422)
        smtp.assert_not_called()

    def test_not_configured_says_so(self):
        env = {k: "" for k in self.SMTP}
        with mock.patch.dict(os.environ, env):
            r = self.call()
        self.assertEqual(r.status_code, 503)
        self.assertIn("not set up", r.get_json()["error"])

    def test_second_click_within_a_minute_is_refused(self):
        with mock.patch.dict(os.environ, self.SMTP), mock.patch("smtplib.SMTP"):
            self.assertEqual(self.call().status_code, 200)
            self.assertEqual(self.call().status_code, 429)

    def _fail_with(self, exc):
        with mock.patch.dict(os.environ, self.SMTP), mock.patch("smtplib.SMTP") as smtp:
            smtp.return_value.__enter__.return_value.login.side_effect = exc
            return self.call()

    def test_wrong_login_is_explained(self):
        import smtplib
        r = self._fail_with(smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed"))
        self.assertEqual(r.status_code, 502)
        msg = r.get_json()["error"]
        self.assertIn("SMTP_USER", msg)
        self.assertNotIn("pw", msg.replace("SMTP_PASSWORD", ""))  # the password never appears

    def test_refused_sender_shows_server_reply(self):
        import smtplib
        r = self._fail_with(smtplib.SMTPSenderRefused(550, b"Sender not valid", "x@gmail.com"))
        self.assertIn("550", r.get_json()["error"])
        self.assertIn("Sender not valid", r.get_json()["error"])

    def test_cannot_connect_is_explained(self):
        r = self._fail_with(ConnectionRefusedError())
        self.assertIn("Could not connect", r.get_json()["error"])

    def test_bad_uid(self):
        self.assertEqual(self.call("../x").status_code, 400)


if __name__ == "__main__":
    unittest.main()
