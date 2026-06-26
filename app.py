import app
import random
import asyncio

from app_components import clear_background
from events.input import Buttons, BUTTON_TYPES
from system.eventbus import eventbus
from system.patterndisplay.events import PatternDisable
from tildagonos import tildagonos


class MemoryLightsApp(app.App):
    LED_PAIRS = {
        1: (12, 1),
        2: (2, 3),
        3: (4, 5),
        4: (6, 7),
        5: (8, 9),
        6: (10, 11),
    }

    BUTTON_NUMBERS = [
        (BUTTON_TYPES["UP"], 1),
        (BUTTON_TYPES["RIGHT"], 2),
        (BUTTON_TYPES["CONFIRM"], 3),
        (BUTTON_TYPES["DOWN"], 4),
        (BUTTON_TYPES["LEFT"], 5),
        (BUTTON_TYPES["CANCEL"], 6),
    ]

    def __init__(self):
        self.screen = "Home"
        self.button_states = Buttons(self)

        self.initial_count = 3
        self.delay = 0.5
        self.sequence_length = self.initial_count
        self.sequence = []

        self.input_index = 0
        self.last_score = None

        self.flash_colour = (0, 80, 255)
        self.success_colour = (0, 255, 0)
        self.fail_colour = (255, 0, 0)

        eventbus.emit(PatternDisable())
        self.clear_leds()

    def clear_leds(self):
        for i in range(1, 13):
            tildagonos.leds[i] = (0, 0, 0)
        tildagonos.leds.write()

    def set_all_leds(self, colour):
        for i in range(1, 13):
            tildagonos.leds[i] = colour
        tildagonos.leds.write()

    def show_pair(self, number, colour=None):
        if colour is None:
            colour = self.flash_colour

        self.clear_leds()
        a, b = self.LED_PAIRS[number]
        tildagonos.leds[a] = colour
        tildagonos.leds[b] = colour
        tildagonos.leds.write()

    def generate_sequence(self):
        self.sequence = [random.randint(1, 6) for _ in range(self.sequence_length)]

    def get_pressed_number(self):
        for button_type, number in self.BUTTON_NUMBERS:
            if self.button_states.get(button_type):
                self.button_states.clear()
                return number
        return None

    async def flash_all(self, colour, render_update, flashes=2, on_time=0.2, off_time=0.15):
        for _ in range(flashes):
            self.set_all_leds(colour)
            await render_update()
            await asyncio.sleep(on_time)

            self.clear_leds()
            await render_update()
            await asyncio.sleep(off_time)

    async def display_sequence(self, render_update):
        self.screen = "Watch"
        self.input_index = 0
        await render_update()

        self.clear_leds()
        await asyncio.sleep(0.4)

        for number in self.sequence:
            self.show_pair(number)
            await render_update()
            await asyncio.sleep(self.delay)

            self.clear_leds()
            await render_update()
            await asyncio.sleep(0.25)

    async def get_player_input(self, render_update):
        self.screen = "Input"
        self.input_index = 0
        await render_update()

        poll_interval = 0.05
        timeout_s = self.delay * 3

        while self.input_index < len(self.sequence):
            waited = 0.0

            while True:
                pressed = self.get_pressed_number()

                if pressed is not None:
                    break

                await asyncio.sleep(poll_interval)
                waited += poll_interval

                if waited >= timeout_s:
                    pressed = 0
                    break

            if pressed != 0:
                self.show_pair(pressed)
                await render_update()
                await asyncio.sleep(0.2)

                self.clear_leds()
                await render_update()

            if pressed != self.sequence[self.input_index]:
                return False

            self.input_index += 1
            await render_update()
            await asyncio.sleep(0.05)

        return True

    async def run_game(self, render_update):
        self.sequence_length = self.initial_count
        self.last_score = None

        while True:
            self.generate_sequence()

            await self.display_sequence(render_update)
            success = await self.get_player_input(render_update)

            if success:
                await self.flash_all(self.success_colour, render_update)

                self.sequence_length += 1
                self.screen = "Level"
                self.clear_leds()
                await render_update()
                await asyncio.sleep(1.2)

            else:
                await self.flash_all(self.fail_colour, render_update)

                self.last_score = self.sequence_length - 1
                self.screen = "Score"
                self.clear_leds()
                await render_update()
                await asyncio.sleep(2.0)

                self.screen = "Home"
                await render_update()
                return

    async def run(self, render_update):
        await render_update()

        while True:
            if self.screen == "Home" and self.button_states.get(BUTTON_TYPES["CANCEL"]):
                self.clear_leds()
                self.button_states.clear()
                self.minimise()
                return

            if self.screen == "Home" and self.button_states.get(BUTTON_TYPES["RIGHT"]):
                self.button_states.clear()
                await self.run_game(render_update)

            await asyncio.sleep(0.05)

    def draw(self, ctx):
        clear_background(ctx)
        ctx.save()
        ctx.rgb(1, 1, 1)

        if self.screen == "Home":
            ctx.move_to(-95, -30).text("Memory Lights")
            ctx.move_to(-95, 0).text("F button exits")
            ctx.move_to(-95, 30).text("B to play")

            if self.last_score is not None:
                ctx.move_to(-95, 60).text("Last score = " + str(self.last_score))

        elif self.screen == "Watch":
            ctx.move_to(-55, -10).text("Watch")
            ctx.move_to(-95, 25).text("Memorise")

        elif self.screen == "Input":
            ctx.move_to(-55, -10).text("Repeat")

        elif self.screen == "Level":
            ctx.move_to(-95, 0).text("Level = " + str(self.sequence_length))

        elif self.screen == "Score":
            ctx.move_to(-95, -10).text("Score = " + str(self.last_score))
            ctx.move_to(-95, 25).text("Game Over")

        ctx.restore()


__app_export__ = MemoryLightsApp