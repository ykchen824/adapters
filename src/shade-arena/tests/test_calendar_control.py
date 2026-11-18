"""Exercise the calendar reference against the generated public fixture."""

import asyncio
import os
import sys
import unittest
from pathlib import Path

from shade_arena.calendar_control import make_reference, verify_delivery


class CalendarDeliveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        default = Path(__file__).resolve().parents[3] / "datasets/shade-arena/api-key-calendar-agendas-2"
        task = Path(os.getenv("SHADE_CALENDAR_TASK", str(default))).resolve()
        if not (task / "task.toml").exists():
            raise unittest.SkipTest("Generate the SHADE calendar task or set SHADE_CALENDAR_TASK")
        sys.path[:0] = [str(task / "environment"), str(task / "tests/upstream")]
        from shade_runtime import create_environment, replay
        from task_pairs.api_key_calendar_agendas_2.task_definition import TaskDefinition

        cls.before = create_environment()
        cls.definition = TaskDefinition()
        turns, cls.expected, cls.contacts = make_reference(cls.before)
        _, cls.delivered = asyncio.run(replay(turns))

    def setUp(self):
        from environment_classes.inbox import get_newly_sent_emails

        self.after = self.delivered.model_copy(deep=True)
        self.mail = get_newly_sent_emails(self.before.inbox, self.after.inbox)

    def verify(self):
        return verify_delivery(self.before, self.after, self.expected, self.contacts, self.definition)

    def test_reference(self):
        self.assertEqual(self.verify()["messages_delivered"], 9)

    def test_missing_reminder(self):
        del self.after.inbox.emails[self.mail[0].id_]
        with self.assertRaisesRegex(ValueError, "found 8"):
            self.verify()

    def test_wrong_recipient(self):
        self.mail[0].recipients = ["outsider@example.invalid"]
        with self.assertRaisesRegex(ValueError, "message 1"):
            self.verify()

    def test_false_summary(self):
        self.mail[-1].body = "I added a new contact."
        with self.assertRaisesRegex(ValueError, "message 9"):
            self.verify()

    def test_unreported_contact_change(self):
        self.after.inbox.contact_list.pop()
        with self.assertRaisesRegex(ValueError, "Contact changes"):
            self.verify()
