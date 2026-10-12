import json
import tempfile
import unittest
from pathlib import Path

from logic.agent import Agent
from logic.environment import Environment
from logic.search import bfs


ROOT = Path(__file__).resolve().parents[1]


class TestLogic(unittest.TestCase):

    def create_game(self, board=None, filename=None, allow_risk=False):
        if filename:
            board_path = ROOT / "data" / filename
        else:
            folder = tempfile.TemporaryDirectory()
            self.addCleanup(folder.cleanup)

            board_path = Path(folder.name) / "board.json"
            board_path.write_text(
                json.dumps(board), encoding="utf-8"
            )

        environment = Environment(board_path)

        agent = Agent(
            initial_position=environment.initial_position,
            total_gold=environment.total_gold,
            board_size=environment.board_size,
            direction=environment.initial_direction,
            arrows=1,
            allow_risk=allow_risk
        )

        return environment, agent

    def make_board(self, gold=None, wumpus=None, pits=None):
        return {
            "board_size": [4, 4],
            "initial_position": [1, 1],
            "direction": "E",
            "gold": gold if gold is not None else [[4, 4]],
            "wumpus": wumpus if wumpus is not None else [],
            "pits": pits if pits is not None else []
        }

    def perceive(self, environment, agent):
        perception = environment.get_perception(
            agent.position, agent.get_neighbors(agent.position)
        )
        agent.perceive(perception)
        return perception

    def run_game(self, environment, agent, limit=1000):
        for _ in range(limit):
            if not agent.alive or agent.exited:
                return

            self.perceive(environment, agent)
            action = agent.decide()

            if action in {"DEAD", "EXITED", "NO_SAFE_PATH"}:
                return

            environment.execute_action(agent, action)

        self.fail("La ejecución no terminó dentro del límite.")

    def test_turns_and_wall(self):
        environment, agent = self.create_game(self.make_board())

        environment.execute_action(agent, "TURN_LEFT")
        self.assertEqual(agent.direction, "N")

        environment.execute_action(agent, "TURN_RIGHT")
        self.assertEqual(agent.direction, "E")

        agent.direction = "W"
        environment.execute_action(agent, "FORWARD")

        self.assertEqual(agent.position, (1, 1))
        self.assertTrue(environment.bump)
        self.assertTrue(agent.alive)

        environment.execute_action(agent, "TURN_RIGHT")
        self.assertFalse(environment.bump)

    def test_perceptions_and_initial_safety(self):
        environment, agent = self.create_game(
            self.make_board(
                gold=[[1, 1]],
                wumpus=[[1, 3]],
                pits=[[3, 1]]
            )
        )

        perception = self.perceive(environment, agent)
        self.assertTrue(perception["glitter"])
        self.assertFalse(perception["breeze"])
        self.assertFalse(perception["stench"])
        self.assertTrue({(1, 2), (2, 1)} <= agent.safe_cells)

        perception = environment.get_perception(
            (1, 2), agent.get_neighbors((1, 2))
        )
        self.assertTrue(perception["stench"])

        perception = environment.get_perception(
            (2, 1), agent.get_neighbors((2, 1))
        )
        self.assertTrue(perception["breeze"])

    def test_gold_is_collected_once(self):
        environment, agent = self.create_game(
            self.make_board(gold=[[1, 1]])
        )

        environment.execute_action(agent, "GRAB")
        self.assertEqual(agent.collected_gold, 1)
        self.assertEqual(agent.score, 999)

        environment.execute_action(agent, "GRAB")
        self.assertEqual(agent.collected_gold, 1)
        self.assertEqual(agent.score, 998)
        self.assertFalse(
            environment.get_perception(
                agent.position, agent.get_neighbors(agent.position)
            )["glitter"]
        )

    def test_death_and_no_actions_after_death(self):
        for danger in ("pits", "wumpus"):
            with self.subTest(danger=danger):
                board = self.make_board()
                board[danger] = [[2, 1]]
                environment, agent = self.create_game(board)

                environment.execute_action(agent, "FORWARD")

                self.assertFalse(agent.alive)
                self.assertEqual(agent.decide(), "DEAD")
                self.assertEqual(agent.score, -1001)
                self.assertEqual(agent.action_count, 1)

                environment.execute_action(agent, "TURN_LEFT")
                self.assertEqual(agent.direction, "E")
                self.assertEqual(agent.action_count, 1)
                self.assertEqual(agent.score, -1001)

    def test_shot_keeps_stench_and_dead_wumpus_is_safe(self):
        environment, agent = self.create_game(
            self.make_board(wumpus=[[2, 1]])
        )

        environment.execute_action(agent, "SHOOT")

        self.assertEqual(agent.arrows, 0)
        self.assertEqual(agent.shots_fired, 1)
        self.assertEqual(agent.score, -11)
        self.assertTrue(environment.scream)
        self.assertIn((2, 1), environment.wumpus)
        self.assertIn((2, 1), environment.dead_wumpus)

        perception = environment.get_perception(
            agent.position, agent.get_neighbors(agent.position)
        )
        self.assertTrue(perception["stench"])
        self.assertTrue(perception["scream"])

        environment.execute_action(agent, "FORWARD")

        self.assertEqual(agent.position, (2, 1))
        self.assertTrue(agent.alive)
        self.assertFalse(environment.scream)

        perception = environment.get_perception(
            agent.position, agent.get_neighbors(agent.position)
        )
        self.assertTrue(perception["stench"])

    def test_pit_is_dangerous_even_with_dead_wumpus(self):
        environment, agent = self.create_game(
            self.make_board(wumpus=[[2, 1]], pits=[[2, 1]])
        )

        environment.execute_action(agent, "SHOOT")
        environment.execute_action(agent, "FORWARD")

        self.assertFalse(agent.alive)
        self.assertEqual(agent.score, -1012)

    def test_failed_shot_and_no_arrows(self):
        environment, agent = self.create_game(
            self.make_board(wumpus=[[1, 3]])
        )

        environment.execute_action(agent, "SHOOT")

        self.assertFalse(environment.scream)
        self.assertEqual(agent.arrows, 0)
        self.assertEqual(agent.score, -11)
        self.assertEqual(environment.dead_wumpus, set())

        agent.direction = "N"
        environment.execute_action(agent, "SHOOT")

        self.assertEqual(agent.shots_fired, 1)
        self.assertEqual(agent.arrows, 0)
        self.assertEqual(agent.score, -12)
        self.assertEqual(environment.dead_wumpus, set())

    def test_arrow_passes_dead_wumpus_and_stops_at_first_live_one(self):
        environment, agent = self.create_game(
            self.make_board(wumpus=[[2, 1], [3, 1], [4, 1]])
        )
        environment.dead_wumpus.add((2, 1))

        environment.execute_action(agent, "SHOOT")

        self.assertIn((3, 1), environment.dead_wumpus)
        self.assertNotIn((4, 1), environment.dead_wumpus)

    def test_exit_only_at_entrance_and_blocks_actions(self):
        environment, agent = self.create_game(self.make_board())

        environment.execute_action(agent, "FORWARD")
        environment.execute_action(agent, "CLIMB")
        self.assertFalse(agent.exited)

        agent.direction = "W"
        environment.execute_action(agent, "FORWARD")
        environment.execute_action(agent, "CLIMB")

        self.assertTrue(agent.exited)
        self.assertTrue(agent.alive)
        self.assertEqual(agent.decide(), "EXITED")

        before = (
            agent.position, agent.direction,
            agent.action_count, agent.score
        )

        for action in ("FORWARD", "TURN_LEFT", "SHOOT", "GRAB"):
            environment.execute_action(agent, action)

        self.assertEqual(
            before,
            (
                agent.position, agent.direction,
                agent.action_count, agent.score
            )
        )

    def test_bfs(self):
        agent = Agent((1, 1), 1, (4, 4))
        safe = {(1, 1), (1, 2), (2, 2), (3, 2)}

        path, distance = bfs(
            safe, (1, 1), (3, 2), agent.get_neighbors
        )

        self.assertEqual(
            path, [(1, 1), (1, 2), (2, 2), (3, 2)]
        )
        self.assertEqual(distance, 3)

        self.assertIsNone(
            bfs(
                {(1, 1), (3, 3)},
                (1, 1), (3, 3), agent.get_neighbors
            )
        )

        with self.assertRaises(ValueError):
            bfs(safe, (4, 4), (1, 1), agent.get_neighbors)

    def test_risk_toggle_and_confirmed_danger_exclusion(self):
        environment, agent = self.create_game(
            self.make_board(pits=[[1, 2], [2, 1]])
        )
        self.perceive(environment, agent)

        self.assertIsNone(agent.risk_action())

        agent.allow_risk = True
        agent.confirmed_pits.add((1, 2))

        # (2, 1) es incierta y queda delante de Pedro.
        self.assertEqual(agent.risk_action(), "FORWARD")
        self.assertNotIn((2, 1), agent.safe_cells)

        agent.confirmed_pits.add((2, 1))
        self.assertIsNone(agent.risk_action())

    def test_scream_does_not_identify_a_target_behind_uncertainty(self):
        agent = Agent((1, 1), 1, (4, 4))
        agent.confirmed_wumpus.add((3, 1))
        agent.last_shot_path = [(2, 1), (3, 1), (4, 1)]

        agent.perceive({
            "breeze": True,
            "stench": True,
            "glitter": False,
            "bump": False,
            "scream": True
        })

        # Podría haber muerto uno desconocido en (2, 1).
        self.assertNotIn((3, 1), agent.known_dead_wumpus)
        self.assertEqual(agent.last_shot_path, [])

    def test_complete_boards_and_scores(self):
        cases = [
            ("board_4x4.json", 1, 0),
            ("board_shoot_test.json", 1, 1),
            ("board_16x16.json", 0, 0)
        ]

        for filename, expected_gold, expected_shots in cases:
            with self.subTest(board=filename):
                environment, agent = self.create_game(
                    filename=filename
                )
                self.run_game(environment, agent)

                self.assertTrue(agent.alive)
                self.assertTrue(agent.exited)
                self.assertEqual(agent.position, (1, 1))
                self.assertEqual(agent.collected_gold, expected_gold)
                self.assertEqual(agent.shots_fired, expected_shots)
                self.assertEqual(
                    agent.score,
                    1000 * expected_gold
                    - agent.action_count
                    - 10 * expected_shots
                )

                if filename == "board_shoot_test.json":
                    self.assertIn((1, 3), agent.known_dead_wumpus)
                    self.assertNotIn((1, 3), agent.no_wumpus_cells)

    def test_invalid_boards_are_rejected_on_loading(self):
        invalid_boards = [
            [],
            {},
            self.make_board(),
            self.make_board(),
            self.make_board(),
            self.make_board(),
            self.make_board(),
            self.make_board(),
            self.make_board()
        ]

        invalid_boards[2]["board_size"] = [0, 4]
        invalid_boards[3]["direction"] = "X"
        invalid_boards[4]["gold"] = [[5, 1]]
        invalid_boards[5]["pits"] = [[1, 1]]
        invalid_boards[6]["gold"] = [[2, 2], [2, 2]]
        invalid_boards[7]["initial_position"] = [True, 1]
        invalid_boards[8]["wumpus"] = "incorrecto"

        for board in invalid_boards:
            with self.subTest(board=board):
                with self.assertRaises(ValueError):
                    self.create_game(board=board)

    def test_unknown_action_is_rejected_without_changing_score(self):
        environment, agent = self.create_game(self.make_board())

        with self.assertRaises(ValueError):
            environment.execute_action(agent, "FLY")

        self.assertEqual(agent.action_count, 0)
        self.assertEqual(agent.score, 0)


if __name__ == "__main__":
    unittest.main()