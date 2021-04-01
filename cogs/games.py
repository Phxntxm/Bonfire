from dataclasses import dataclass
from discord.ext import commands

import collections
import utils


@dataclass
class JPWord:
    kanji: str
    reading: str

    def __eq__(self, other):
        return (
            isinstance(other, JPWord)
            and self.kanji == other.kanji
            and self.reading == other.reading
        )

    def __hash__(self):
        return hash(self.kanji + self.reading)


class Shiritori:
    def __init__(self):
        self.losers = []
        self.players = []
        self.last_kana = None
        self.last_player = None
        self.used_words = []

    # This won't include small tsu because for this use case
    small_kanas = ["ゃ", "ゅ", "ょ", "ぁ", "ぃ", "ぅ", "ぇ", "ぉ"]

    def get_first_kana(self, word: JPWord):
        i = iter(word.reading)

        for char in i:
            # I don't know why someone would do it, but something like 「りんご」
            # I'd want to ignore the []
            if char.isalpha():
                # If there is a small kana, like りゅ then we want both
                try:
                    n = next(i)
                except StopIteration:
                    return char
                else:
                    if n in self.small_kanas:
                        return f"{char}{n}"
                    else:
                        return char

    def get_last_kana(self, word: JPWord):
        i = reversed(word.reading)

        for char in i:
            # Ignore anything in case they end with something like ！ or ？
            if char.isalpha():
                # If the last one is a small kana (other than つ)
                if char in self.small_kanas:
                    return f"{next(i)}{char}"
                else:
                    return char

    def cull_words(self, words: list):
        """Removes readings that will not fit based on last used kana"""
        c = words.copy()
        for word in words:
            first = self.get_first_kana(word)

            if self.last_kana is not None and first != self.last_kana:
                c.remove(word)

        return c

    async def player_lost(self, ctx: commands.Context, msg: str = None):
        """Sends a player lost message, tracks players losing, and returns
        based on whether or not the game is now over"""
        self.losers.append(ctx.author)
        self.players.remove(ctx.author)

        if msg:
            await ctx.send(msg)

        return len(self.players) == 1

    async def readings_for_word(self, word: str):
        """This goes through the list that jisho API gives us and returns the right reading and word
        This does no validation of kana, this is only for the proper kanji/reading pairs that the player
        was possibly meaning to use"""
        data = await utils.request(
            "https://jisho.org/api/v1/search/words", payload={"keyword": word}
        )

        possibilities = set()

        for slug in data["data"]:
            is_noun = False
            # Determinte if this slug is a noun
            for sense in slug["senses"]:
                if "Noun" in sense["parts_of_speech"]:
                    is_noun = True
                    break
            # If this isn't a noun we don't even care
            if not is_noun:
                continue
            # Now go through definitions to get readings/kanji
            for japanese in slug["japanese"]:
                # They can enter either the kanji or the reading they want, compare both
                _word = japanese.get("word")
                reading = japanese.get("reading")

                # If there are readings of this word that have a paired kanji, prefer that
                if _word is None and possibilities:
                    continue
                elif _word is None:
                    possibilities.add(JPWord("", reading))

                # If the provided kanji/reading is right, then add it as a possibility
                if _word == word or reading == word:
                    possibilities.add(JPWord(_word, reading))

        return list(possibilities)

    async def validate_word(self, ctx: commands.Context, word: str):
        # First make sure the we ensure the player is tracked
        if ctx.author in self.losers:
            await ctx.message.add_reaction("❌")
            return False
        if ctx.author not in self.players:
            self.players.append(ctx.author)

        # Get the words that could have been meant
        words = await self.readings_for_word(word)

        # Validate that any words were returned
        if not words:
            msg = f"{ctx.author} loses, only Japanese nouns can be used"
            # msg += f"\n{ctx.author}の勝利。日本語の名詞のみ使用できる"
            return await self.player_lost(ctx, msg)
        # Validate there are still words, if not then the last kana wasn't right
        words = self.cull_words(words)
        if self.last_kana is not None and not words:
            msg = f'{ctx.author} loses, you must enter a word that begins with "{self.last_kana}"'
            # msg += f"\n{ctx.author}の勝利。「{self.last_kana}」から始まる言葉を入力しなくてはなりません"
            return await self.player_lost(ctx, msg)
        # Validate it's more than one syllable
        words = [word for word in words if len(word.reading) > 1]
        if not words:
            msg = f"{ctx.author} please only use words with more than one syllable"
            # msg += f"\n{ctx.author}、複数の音節を持つ単語のみを使用してください"
            await ctx.send(msg)
            return False
        # If we're here, we have one (or more, but we care about the first) matching word
        # just base on that from now on
        word = words[0]
        # Validate against words used
        if word in self.used_words:
            msg = f"{ctx.author} loses, {word} has already been used"
            # msg += f"\n{ctx.author}の勝利。「{word}」は既に使用されている"
            return await self.player_lost(ctx, msg)
        # Validate against ん and ン
        last_kana = self.get_last_kana(word)
        if last_kana in ("ん", "ン"):
            msg = f"{ctx.author} loses, last letter cannot be ん"
            # msg += f"\n{ctx.author}の勝利。最後の仮名を「ん」にすることはできない"
            return await self.player_lost(ctx, msg)
        # Append the first matched word since we have one
        self.used_words.append(word)
        self.last_kana = last_kana
        self.last_player = ctx.author
        await ctx.message.add_reaction("🟢")
        return False


class Games(commands.Cog):
    def __init__(self):
        self.running_games = collections.defaultdict(dict)

    @commands.command(aliases=["word_chain", "しりとり", "シリトリ"])
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @utils.checks.can_run(send_messages=True)
    async def shiritori(self, ctx, *, word):
        """
        Starts or play on a game of Shiritori, in which the last letter of the last word given
        has to be the first letter of the next word given. For example, if the word given is
        apple, then the next word can be elephant because apple ends in e and elephant begins in e

        The last player who entered a word cannot be the next person who enters a word
        The kana ん cannot be used, as no word in Japanese starts with this
        The word used cannot be a previously given word
        """
        # Ensure only one game is happening at once
        game = self.running_games["shiritori"].get(ctx.channel.id)
        if game is None:
            game = Shiritori()
            self.running_games["shiritori"][ctx.channel.id] = game

        if await game.validate_word(ctx, word):
            winner = game.players[0]
            msg = f"{winner} wins!"
            # msg += f"\n{winner}の負け"
            await ctx.send(msg)
            del self.running_games["shiritori"][ctx.channel.id]


def setup(bot):
    bot.add_cog(Games())
