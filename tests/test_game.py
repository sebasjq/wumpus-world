import json
import unittest
from pathlib import Path

from logic.game import Game


ROOT = Path(__file__).resolve().parents[1]


class TestGame(unittest.TestCase):

    def create_game(
        self,
        filename="board_shoot_test.json",
        allow_risk=False,
        arrows=1
    ):
        return Game(
            ROOT / "data" / filename,
            allow_risk=allow_risk,
            arrows=arrows
        )

    def finish_game(self, game, limit=1500):
        for _ in range(limit):
            state = game.step()

            if state["status"] != "running":
                return state

        self.fail("La partida no terminó dentro del límite.")

    def test_initial_state_and_json(self):
        game = self.create_game()
        state = game.get_state()

        self.assertEqual(state["status"], "running")
        self.assertIsNone(state["last_action"])
        self.assertEqual(state["board_size"], [4, 4])
        self.assertEqual(state["agent"]["position"], [1, 1])
        self.assertEqual(state["agent"]["direction"], "E")
        self.assertEqual(state["agent"]["action_count"], 0)
        self.assertEqual(state["agent"]["score"], 0)

        self.assertEqual(state["world"]["gold"], [[1, 3]])
        self.assertEqual(state["world"]["live_wumpus"], [[1, 3]])
        self.assertEqual(state["world"]["dead_wumpus"], [])
        self.assertIn([3, 1], state["world"]["pits"])
        self.assertIn([1, 1], state["knowledge"]["visited"])

        # Todos los datos deben poder convertirse en JSON.
        serialized = json.dumps(state, allow_nan=False)
        self.assertEqual(json.loads(serialized), state)

    def test_get_state_does_not_advance(self):
        game = self.create_game()
        before = game.get_state()

        for _ in range(3):
            self.assertEqual(game.get_state(), before)

        self.assertEqual(game.agent.action_count, 0)

    def test_response_does_not_modify_internal_state(self):
        game = self.create_game()
        original = game.get_state()
        response = game.get_state()

        response["agent"]["position"][0] = 99
        response["world"]["gold"].clear()
        response["world"]["pits"].clear()
        response["knowledge"]["safe_cells"].clear()
        response["perception"]["stench"] = True

        self.assertEqual(game.get_state(), original)

    def test_step_executes_one_action_and_reports_turn(self):
        game = self.create_game()

        state = game.step()

        self.assertEqual(state["last_action"], "TURN_LEFT")
        self.assertEqual(state["agent"]["position"], [1, 1])
        self.assertEqual(state["agent"]["direction"], "N")
        self.assertEqual(state["agent"]["action_count"], 1)
        self.assertEqual(state["agent"]["score"], -1)

        state = game.step()

        self.assertEqual(state["last_action"], "FORWARD")
        self.assertEqual(state["agent"]["position"], [1, 2])
        self.assertEqual(state["agent"]["action_count"], 2)

        # La percepción corresponde a la posición después del avance.
        self.assertTrue(state["perception"]["stench"])

    def test_shot_reports_scream_ammunition_and_dead_wumpus(self):
        game = self.create_game()

        for _ in range(100):
            state = game.step()

            if state["last_action"] == "SHOOT":
                break
        else:
            self.fail("Pedro no realizó el disparo esperado.")

        self.assertTrue(state["perception"]["scream"])
        self.assertTrue(state["perception"]["stench"])
        self.assertEqual(state["agent"]["arrows"], 0)
        self.assertEqual(state["agent"]["shots_fired"], 1)
        self.assertEqual(state["world"]["dead_wumpus"], [[1, 3]])
        self.assertEqual(state["world"]["live_wumpus"], [])
        self.assertIn(
            [1, 3], state["knowledge"]["known_dead_wumpus"]
        )
        self.assertIn([1, 3], state["knowledge"]["safe_cells"])

        # Consultar no borra el grito ni ejecuta otra acción.
        self.assertEqual(game.get_state(), state)

    def test_gold_collection_is_reflected_in_response(self):
        game = self.create_game()

        for _ in range(100):
            state = game.step()

            if state["last_action"] == "GRAB":
                break
        else:
            self.fail("Pedro no recogió el oro esperado.")

        self.assertEqual(state["agent"]["collected_gold"], 1)
        self.assertEqual(state["agent"]["remaining_gold"], 0)
        self.assertEqual(state["world"]["gold"], [])
        self.assertFalse(state["perception"]["glitter"])

    def test_success_and_no_steps_after_finishing(self):
        game = self.create_game()
        final_state = self.finish_game(game)

        self.assertEqual(final_state["status"], "success")
        self.assertEqual(final_state["last_action"], "CLIMB")
        self.assertEqual(final_state["agent"]["position"], [1, 1])
        self.assertTrue(final_state["agent"]["alive"])
        self.assertTrue(final_state["agent"]["exited"])
        self.assertEqual(final_state["agent"]["collected_gold"], 1)
        self.assertEqual(final_state["agent"]["remaining_gold"], 0)
        self.assertEqual(final_state["agent"]["score"], 962)
        self.assertIsNone(final_state["perception"])

        for _ in range(3):
            self.assertEqual(game.step(), final_state)

    def test_retreat_with_gold_pending(self):
        game = self.create_game(filename="board_16x16.json")
        state = self.finish_game(game)

        self.assertEqual(state["status"], "retreated")
        self.assertTrue(state["agent"]["alive"])
        self.assertTrue(state["agent"]["exited"])
        self.assertEqual(state["agent"]["position"], [1, 1])
        self.assertEqual(state["agent"]["collected_gold"], 0)
        self.assertEqual(state["agent"]["remaining_gold"], 37)
        self.assertEqual(state["agent"]["score"], -11)
        self.assertEqual(game.step(), state)

    def test_death_and_no_steps_after_death(self):
        game = self.create_game(
            filename="board_no_safe_path_test.json",
            allow_risk=True
        )
        state = self.finish_game(game)

        self.assertEqual(state["status"], "dead")
        self.assertFalse(state["agent"]["alive"])
        self.assertFalse(state["agent"]["exited"])
        self.assertEqual(state["last_action"], "FORWARD")
        self.assertIsNone(state["perception"])
        self.assertEqual(
            state["agent"]["score"],
            -state["agent"]["action_count"] - 1000
        )
        self.assertEqual(game.step(), state)

    def test_reset_restores_finished_game(self):
        game = self.create_game(arrows=3)
        original = game.get_state()

        self.finish_game(game)
        reset_state = game.reset()

        self.assertEqual(reset_state, original)
        self.assertEqual(reset_state["agent"]["arrows"], 3)
        self.assertEqual(reset_state["agent"]["shots_fired"], 0)
        self.assertEqual(reset_state["agent"]["score"], 0)
        self.assertEqual(reset_state["world"]["dead_wumpus"], [])

    def test_risk_changes_and_survives_reset(self):
        game = self.create_game()

        enabled = game.set_risk(True)
        self.assertTrue(enabled["allow_risk"])
        self.assertTrue(game.agent.allow_risk)
        self.assertTrue(game.reset()["allow_risk"])

        disabled = game.set_risk(False)
        self.assertFalse(disabled["allow_risk"])
        self.assertFalse(game.agent.allow_risk)
        self.assertFalse(game.reset()["allow_risk"])

        # Cambiar una opción no ejecuta acciones.
        self.assertEqual(game.agent.action_count, 0)

    def test_zero_arrows_disables_shooting(self):
        game = self.create_game(arrows=0)
        state = self.finish_game(game)

        self.assertEqual(state["status"], "retreated")
        self.assertEqual(state["agent"]["arrows"], 0)
        self.assertEqual(state["agent"]["shots_fired"], 0)
        self.assertEqual(state["world"]["live_wumpus"], [[1, 3]])

    def test_invalid_options_are_rejected(self):
        for arrows in (-1, 0.5, True, "2", None):
            with self.subTest(arrows=arrows):
                with self.assertRaises(ValueError):
                    self.create_game(arrows=arrows)

        for risk in (0, 1, "True", None):
            with self.subTest(risk=risk):
                with self.assertRaises(ValueError):
                    self.create_game(allow_risk=risk)

        game = self.create_game()
        before = game.get_state()

        with self.assertRaises(ValueError):
            game.set_risk("False")

        self.assertEqual(game.get_state(), before)


if __name__ == "__main__":
    unittest.main()