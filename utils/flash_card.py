import random
import discord
from discord.ext import menus


class FlashCard:
    def __init__(self, vocab, sentence, reading, answer):
        self.vocab = vocab
        self.sentence = sentence
        self.reading = reading
        self.answer = answer

    def show_question(self):
        return discord.Embed(
            description=f"""
            **Vocabulary**: {self.vocab}
            """
        )

    def show_hint(self):
        return discord.Embed(
            description=f"""
            **Vocabulary**: {self.vocab}
            **Example sentence**: {self.sentence}
            """
        )

    def show_answer(self):
        return discord.Embed(
            description=f"""
            **Vocabulary**: {self.vocab}
            """  # **Example sentence**: {self.sentence}
            f"""
            **Reading**: {self.reading}
            **Meaning**: {self.answer}
            """
        )


class FlashCardDisplay(menus.Menu):
    def __init__(self, pack):
        super().__init__(clear_reactions_after=True)
        self.pack = pack
        self.current_card = pack.pop()
        self.showing_answer = False
        self.incorrect = 0
        self.correct = 0

    async def send_initial_message(self, ctx, channel):
        await ctx.send(
            "Instructions: You'll be shown a vocabulary word. "
            "If you know/don't know the answer hit ▶️. The answer will then "
            "be shown, and you can choose 🔴 if you didn't know the answer or 🟢 if you did."
        )
        embed = self.modify_embed(self.current_card.show_question())
        return await self.ctx.send(embed=embed)

    def next_card(self, reinsert=False):
        try:
            if reinsert:
                spot = random.randint(0, round(len(self.pack) * 3 / 4 - 1))
                self.pack.insert(spot, self.current_card)
            self.current_card = self.pack.pop()
            return self.modify_embed(self.current_card.show_question())
        except IndexError:
            self.stop()
            embed = discord.Embed(
                description=f"Got {self.correct}/{self.incorrect + self.correct} right. "
                f"{self.correct/(self.incorrect + self.correct) * 100:.2f}%"
            )
            embed = embed.set_author(
                name=self.ctx.author, icon_url=self.ctx.author.avatar_url
            )
            return embed

    def modify_embed(self, embed):
        embed = embed.set_footer(text=f"{len(self.pack) + 1} cards left")
        embed = embed.set_author(
            name=self.ctx.author, icon_url=self.ctx.author.avatar_url
        )
        return embed

    # @menus.button("❔")
    # async def do_hint(self, payload):
    #     embed = self.modify_embed(self.current_card.show_hint())
    #     return await self.message.edit(embed=embed)

    @menus.button("▶️")
    async def do_flip(self, payload):
        self.showing_answer = True
        embed = self.modify_embed(self.current_card.show_answer())
        return await self.message.edit(embed=embed)

    @menus.button("🔴")
    async def do_failure(self, payload):
        if not self.showing_answer:
            return
        self.incorrect += 1
        self.showing_answer = False
        embed = self.next_card(reinsert=True)
        return await self.message.edit(embed=embed)

    @menus.button("🟢")
    async def do_correct(self, payload):
        if not self.showing_answer:
            return
        self.correct += 1
        self.showing_answer = False
        embed = self.next_card()
        return await self.message.edit(embed=embed)
