import discord
from discord.ext import menus


class FlashCard:
    def __init__(self, vocab, sentence, answer):
        self.vocab = vocab
        self.sentence = sentence
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
            """
            **Answer**: {self.answer}
            """
        )


class FlashCardDisplay(menus.Menu):
    def __init__(self, pack):
        super().__init__(clear_reactions_after=True)
        self.pack = pack
        self.count = 0
        self.current_card = pack[self.count]
        self.amount_of_cards = len(pack)
        self.showing_answer = False

    async def send_initial_message(self, ctx, channel):
        await ctx.send(
            "Instructions: You'll be shown a vocabulary word. "
            "If you know/don't know the answer hit ▶️. The answer will then "
            "be shown, and you can choose 🔴 if you didn't know the answer or 🟢 if you did."
        )
        embed = self.modify_embed(self.current_card.show_question())
        return await self.ctx.send(embed=embed)

    def next_card(self):
        try:
            self.count += 1
            self.current_card = self.pack[self.count]
            return self.modify_embed(self.current_card.show_question())
        except IndexError:
            # Probably show results
            self.stop()

    def modify_embed(self, embed):
        embed = embed.set_footer(text=f"{self.count + 1}/{self.amount_of_cards}")
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
        # Save that they got it wrong
        self.showing_answer = False
        embed = self.next_card()
        return await self.message.edit(embed=embed)

    @menus.button("🟢")
    async def do_correct(self, payload):
        if not self.showing_answer:
            return
        # Save that they got it right
        self.showing_answer = False
        embed = self.next_card()
        return await self.message.edit(embed=embed)
