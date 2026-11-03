import unittest
from arena.core import ArenaError,ROOT,read_json,scratch_directory
from arena_web.data import Store


class ParticipantGroupTests(unittest.TestCase):
    def test_overlapping_memberships_are_metadata_and_do_not_change_saved_competitions(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            local=store.save_participant_group('Local',['mock-single'])
            free=store.save_participant_group('Free',['mock-single','mock-repair'])
            config=read_json(ROOT/'configs/offline-complete.json')
            draft=store.save_draft(config)
            store.set_participant_groups('mock-single',[local['id'],free['id']])
            self.assertTrue(all('mock-single' in group['members'] for group in store.participant_groups()))
            store.save_participant_group('Renamed local',[],local['id'])
            self.assertEqual(store.draft(draft['id'])['config'],config)
            self.assertIn('mock-single',next(g for g in store.participant_groups() if g['id']==free['id'])['members'])
            self.assertNotIn('groups',next(m for m in store.catalog() if m['id']=='mock-single'))
            self.assertEqual(Store(root/'runs',root/'settings').participant_groups(),store.participant_groups())

    def test_invalid_membership_changes_are_atomic_and_deletion_cleans_only_group_metadata(self):
        with scratch_directory() as root:
            store=Store(root/'runs',root/'settings')
            group=store.save_participant_group('Free',['mock-single','mock-single'])
            self.assertEqual(group['members'],['mock-single'])
            before=store.participant_groups()
            with self.assertRaises(ArenaError):store.set_participant_groups('mock-single',[group['id'],'missing'])
            with self.assertRaises(ArenaError):store.save_participant_group('Bad',['unknown'])
            with self.assertRaises(ArenaError):store.save_participant_group('free',[])
            self.assertEqual(store.participant_groups(),before)
            store.delete_participant('mock-single')
            self.assertEqual(store.participant_groups()[0]['members'],[])
            store.delete_participant_group(group['id'])
            self.assertEqual(store.participant_groups(),[])
            self.assertTrue(any(m['id']=='mock-repair' for m in store.catalog()))
