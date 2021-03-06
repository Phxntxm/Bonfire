import discord
from enum import Enum
from discord.ext import menus


class GodanEndingTypes(Enum):
    u = 1
    tsu_ru = 2
    mu_bu_nu = 3
    ku = 4
    gu = 5
    su = 6


godan_transformation = {
    "ぐ": {"あ": "が", "い": "ぎ", "え": "げ", "お": "ご"},
    "す": {"あ": "さ", "い": "し", "え": "せ", "お": "そ"},
    "く": {"あ": "か", "い": "き", "え": "け", "お": "こ"},
    "ぬ": {"あ": "な", "い": "に", "え": "ね", "お": "の"},
    "む": {"あ": "ま", "い": "み", "え": "め", "お": "も"},
    "う": {"あ": "あ", "い": "い", "え": "え", "お": "お"},
    "ぶ": {"あ": "ば", "い": "び", "え": "べ", "お": "ぼ"},
    "つ": {"あ": "た", "い": "ち", "え": "て", "お": "と"},
    "る": {"あ": "ら", "い": "り", "え": "れ", "お": "ろ"},
}


class ConjugationMenu(menus.ListPageSource):
    def __init__(self, data):
        self.main = data.pop("main")
        self.type = data.pop("type")
        super().__init__(data.pop("verbs"), per_page=1)

    async def format_page(self, menu, entry):
        offset = menu.current_page * self.per_page
        e = discord.Embed(title=f"Conjugation guide for {self.main}")
        e.description = "\n\n".join(
            f"**{form_type}**\n**Rule:** {rule}\n**Conjugation:** {form}"
            for form_type, (rule, form) in entry.items()
        )
        e.set_footer(text=f"{offset+1}/{self.get_max_pages()} pages")
        return e


class Verbs:
    def __init__(self, verb):
        if verb == "来る":
            verb = "くる"
        self.verb = verb
        self.stem = self.verb[:-1]
        self.ending = self.verb[-1]

        if self.ending == "う":
            self.godan_ending_type = GodanEndingTypes.u
        elif self.ending in ["つ", "る"]:
            self.godan_ending_type = GodanEndingTypes.tsu_ru
        elif self.ending in ["む", "ぶ", "ぬ"]:
            self.godan_ending_type = GodanEndingTypes.mu_bu_nu
        elif self.ending == "く":
            self.godan_ending_type = GodanEndingTypes.ku
        elif self.ending == "ぐ":
            self.godan_ending_type = GodanEndingTypes.gu
        elif self.ending == "す":
            self.godan_ending_type = GodanEndingTypes.su

    def te_form(self):
        raise NotImplementedError()

    def verb_stem(self, ending="い"):
        raise NotImplementedError()

    def negative_te_form(self):
        raise NotImplementedError()

    def masu_form(self):
        raise NotImplementedError()

    def masen_form(self):
        raise NotImplementedError()

    def mashita_form(self):
        raise NotImplementedError()

    def masendeshita_form(self):
        raise NotImplementedError()

    def dictionary_form(self):
        raise NotImplementedError()

    def nai_form(self):
        raise NotImplementedError()

    def ta_form(self):
        raise NotImplementedError()

    def nakatta_form(self):
        raise NotImplementedError()

    def ba_form(self):
        raise NotImplementedError()

    def negative_ba_form(self):
        raise NotImplementedError()

    def tara_form(self):
        raise NotImplementedError()

    def negative_tara_form(self):
        raise NotImplementedError()

    def imperative_form(self):
        raise NotImplementedError()

    def formal_imperative_form(self):
        raise NotImplementedError()

    def volitional_form(self):
        raise NotImplementedError()

    def formal_volitional_form(self):
        raise NotImplementedError()

    def potential_form(self):
        raise NotImplementedError()

    def passive_form(self):
        raise NotImplementedError()

    def causative_form(self):
        raise NotImplementedError()

    def causative_passive_form(self):
        raise NotImplementedError()

    async def display(self, ctx):
        data = {
            "main": self.verb,
            "type": self.verb_type,
            "verbs": [
                {
                    "Polite present affirmative": self.masu_form(),
                    "Polite present negative": self.masen_form(),
                    "Polite past affirmative": self.mashita_form(),
                    "Polite past negative": self.masendeshita_form(),
                },
                {
                    "Plain present affirmative": self.dictionary_form(),
                    "Plain present negative": self.nai_form(),
                    "Plain past affirmative": self.ta_form(),
                    "Plain past negative": self.nakatta_form(),
                },
                {
                    "Te form": self.te_form(),
                    "Negative te form": self.negative_te_form(),
                },
                {
                    "General conditional": self.ba_form(),
                    "General conditional negative": self.negative_ba_form(),
                    "Hypothetical conditional": self.tara_form(),
                    "Hypothetical conditional negative": self.negative_tara_form(),
                },
                {
                    "Imperative": self.imperative_form(),
                    "Formal imperative": self.formal_imperative_form(),
                    "Suggestion": self.volitional_form(),
                    "Formal suggestion": self.formal_volitional_form(),
                },
                {
                    "Potential": self.potential_form(),
                    "Passive": self.passive_form(),
                    "Causative": self.causative_form(),
                    "Causative Passive": self.causative_passive_form(),
                },
            ],
        }

        pages = menus.MenuPages(
            source=ConjugationMenu(data), clear_reactions_after=True
        )
        await pages.start(ctx)


class GodanVerbs(Verbs):
    verb_type = "Godan"

    def verb_stem(self, ending="い"):
        return f"{self.stem}{godan_transformation[self.ending][ending]}"

    def te_form(self):
        rule = (
            "If the ending is う、つ、る replace it with って.\n"
            "If the ending is む、ぶ、ぬ replace it with んで.\n"
            "If the ending is く replace it with いて.\n"
            "If the ending is ぐ replace it with いで.\n"
            "If the ending is す replace it with して."
        )
        if (
            self.godan_ending_type is GodanEndingTypes.u
            or self.godan_ending_type is GodanEndingTypes.tsu_ru
        ):
            return rule, f"{self.stem}って"
        elif self.godan_ending_type is GodanEndingTypes.mu_bu_nu:
            return rule, f"{self.stem}んで"
        elif self.godan_ending_type is GodanEndingTypes.ku:
            return rule, f"{self.stem}いて"
        elif self.godan_ending_type is GodanEndingTypes.gu:
            return rule, f"{self.stem}いで"
        elif self.godan_ending_type is GodanEndingTypes.su:
            return rule, f"{self.stem}して"

    def negative_te_form(self):
        rule = (
            "If the ending is う、 replace it with わ. Then add なくて regardless of ending"
        )
        if self.godan_ending_type is GodanEndingTypes.u:
            return rule, f"{self.stem}わなくて"
        else:
            return rule, f"{self.verb_stem('あ')}なくて"

    def masu_form(self):
        rule = "Replace the ending with the corresponding い kana, then add ます"
        return rule, f"{self.verb_stem('い')}ます"

    def masen_form(self):
        rule = "Replace the ending with the corresponding い kana, then add ません"
        return rule, f"{self.verb_stem('い')}ません"

    def mashita_form(self):
        rule = "Replace the ending with the corresponding い kana, then add ました"
        return rule, f"{self.verb_stem('い')}ました"

    def masendeshita_form(self):
        rule = "Replace the ending with the corresponding い kana, then add ませんでした"
        return rule, f"{self.verb_stem('い')}ませんでした"

    def dictionary_form(self):
        rule = "The verb stem is followed by the corresponding う kana"
        return rule, self.verb

    def nai_form(self):
        rule = "If the ending is う、 replace it with わ. Then add ない regardless of ending"
        if self.godan_ending_type is GodanEndingTypes.u:
            return rule, f"{self.stem}わない"
        else:
            return rule, f"{self.verb_stem('あ')}ない"

    def ta_form(self):
        rule = (
            "If the ending is う、つ、る replace it with った.\n"
            "If the ending is む、ぶ、ぬ replace it with んだ.\n"
            "If the ending is く replace it with いた.\n"
            "If the ending is ぐ replace it with いだ.\n"
            "If the ending is す replace it with した."
        )
        if (
            self.godan_ending_type is GodanEndingTypes.u
            or self.godan_ending_type is GodanEndingTypes.tsu_ru
        ):
            return rule, f"{self.stem}った"
        elif self.godan_ending_type is GodanEndingTypes.mu_bu_nu:
            return rule, f"{self.stem}んだ"
        elif self.godan_ending_type is GodanEndingTypes.ku:
            return rule, f"{self.stem}いた"
        elif self.godan_ending_type is GodanEndingTypes.gu:
            return rule, f"{self.stem}いだ"
        elif self.godan_ending_type is GodanEndingTypes.su:
            return rule, f"{self.stem}した"

    def nakatta_form(self):
        rule = (
            "If the ending is う、 replace it with わ. Then add なかった regardless of ending"
        )
        if self.godan_ending_type is GodanEndingTypes.u:
            return rule, f"{self.stem}わなかった"
        else:
            return rule, f"{self.verb_stem('あ')}なかった"

    def ba_form(self):
        rule = (
            "If the ending is う、つ、る replace it with えば.\n"
            "If the ending is む、ぶ、ぬ replace it with めば.\n"
            "If the ending is く replace it with いけば.\n"
            "If the ending is ぐ replace it with けば.\n"
            "If the ending is す replace it with せば."
        )
        if (
            self.godan_ending_type is GodanEndingTypes.u
            or self.godan_ending_type is GodanEndingTypes.tsu_ru
        ):
            return rule, f"{self.stem}えば"
        elif self.godan_ending_type is GodanEndingTypes.mu_bu_nu:
            return rule, f"{self.stem}めば"
        elif self.godan_ending_type is GodanEndingTypes.ku:
            return rule, f"{self.stem}いけば"
        elif self.godan_ending_type is GodanEndingTypes.gu:
            return rule, f"{self.stem}げば"
        elif self.godan_ending_type is GodanEndingTypes.su:
            return rule, f"{self.stem}せば"

    def negative_ba_form(self):
        rule = (
            "If the ending is う、 replace it with わ. Then add なければ regardless of ending"
        )
        if self.godan_ending_type is GodanEndingTypes.u:
            return rule, f"{self.stem}わなければ"
        else:
            return rule, f"{self.verb_stem('あ')}なければ"

    def tara_form(self):
        rule = (
            "If the ending is う、つ、る replace it with ったら.\n"
            "If the ending is む、ぶ、ぬ replace it with んだら.\n"
            "If the ending is く replace it with いたら.\n"
            "If the ending is ぐ replace it with いだら.\n"
            "If the ending is す replace it with したら."
        )
        if (
            self.godan_ending_type is GodanEndingTypes.u
            or self.godan_ending_type is GodanEndingTypes.tsu_ru
        ):
            return rule, f"{self.stem}ったら"
        elif self.godan_ending_type is GodanEndingTypes.mu_bu_nu:
            return rule, f"{self.stem}んだら"
        elif self.godan_ending_type is GodanEndingTypes.ku:
            return rule, f"{self.stem}いたら"
        elif self.godan_ending_type is GodanEndingTypes.gu:
            return rule, f"{self.stem}いだら"
        elif self.godan_ending_type is GodanEndingTypes.su:
            return rule, f"{self.stem}したら"

    def negative_tara_form(self):
        rule = (
            "If the ending is う、 replace it with わ. Then add なｋったら regardless of ending"
        )
        if self.godan_ending_type is GodanEndingTypes.u:
            return rule, f"{self.stem}わなかったら"
        else:
            return rule, f"{self.verb_stem('あ')}なかったら"

    def imperative_form(self):
        rule = "Replace the ending with the corresponding え form"
        return rule, f"{self.verb_stem('え')}"

    def formal_imperative_form(self):
        rule = "Replace the ending with the corresponding い form. Then add なさい"
        return rule, f"{self.verb_stem('い')}なさい"

    def volitional_form(self):
        rule = "Replace the ending with the corresponding お form. Then add う"
        return rule, f"{self.verb_stem('お')}う"

    def formal_volitional_form(self):
        rule = "Replace the ending with the corresponding い form. Then add ましょう"
        return rule, f"{self.verb_stem('い')}ましょう"

    def potential_form(self):
        rule = "Replace the ending with the corresponding え form. Then add る"
        return rule, f"{self.verb_stem('え')}る"

    def passive_form(self):
        rule = "Replace the ending with the corresponding あ form. Then add れる"
        return rule, f"{self.verb_stem('あ')}れる"

    def causative_form(self):
        rule = "Replace the ending with the corresponding あ form. Then add せる"
        return rule, f"{self.verb_stem('あ')}せる"

    def causative_passive_form(self):
        rule = "Replace the ending with the corresponding あ form. Then add せられる"
        return rule, f"{self.verb_stem('あ')}せられる"


class IchidanVerbs(Verbs):
    verb_type = "Godan"

    def te_form(self):
        rule = "Attach て to the verb stem"
        return rule, f"{self.verb_stem()}て"

    def verb_stem(self, ending="い"):
        return self.stem

    def negative_te_form(self):
        rule = "Attach ないで to the verb stem"
        return rule, f"{self.verb_stem()}ないで"

    def masu_form(self):
        rule = "Attach ます to the verb stem"
        return rule, f"{self.verb_stem()}ます"

    def masen_form(self):
        rule = "Attach ません to the verb stem"
        return rule, f"{self.verb_stem()}ません"

    def mashita_form(self):
        rule = "Attach ました to the verb stem"
        return rule, f"{self.verb_stem()}ました"

    def masendeshita_form(self):
        rule = "Attach ませんでした to the verb stem"
        return rule, f"{self.verb_stem()}ませんでした"

    def dictionary_form(self):
        rule = "The verb stem followed by る"
        return rule, self.verb

    def nai_form(self):
        rule = "Attach ない to the verb stem"
        return rule, f"{self.verb_stem()}ない"

    def ta_form(self):
        rule = "Attach た to the verb stem"
        return rule, f"{self.verb_stem()}た"

    def nakatta_form(self):
        rule = "Attach なかった to the verb stem"
        return rule, f"{self.verb_stem()}なかった"

    def ba_form(self):
        rule = "Attach れば to the verb stem"
        return rule, f"{self.verb_stem()}れば"

    def negative_ba_form(self):
        rule = "Attach なければ to the verb stem"
        return rule, f"{self.verb_stem()}なければ"

    def tara_form(self):
        rule = "Attach たら to the verb stem"
        return rule, f"{self.verb_stem()}たら"

    def negative_tara_form(self):
        rule = "Attach なかったら to the verb stem"
        return rule, f"{self.verb_stem()}なかったら"

    def imperative_form(self):
        rule = "The ending る becomes れ"
        return rule, f"{self.verb_stem()[:-1]}れ"

    def formal_imperative_form(self):
        rule = "Attach なさい to the verb stem"
        return rule, f"{self.verb_stem()}なさい"

    def volitional_form(self):
        rule = "Attach よう to the verb stem"
        return rule, f"{self.verb_stem()}よう"

    def formal_volitional_form(self):
        rule = "Attach ましょう to the verb stem"
        return rule, f"{self.verb_stem()}ましょう"

    def potential_form(self):
        rule = "Attach られる to the verb stem"
        return rule, f"{self.verb_stem()}られる"

    def passive_form(self):
        rule = "Attach られる to the verb stem"
        return rule, f"{self.verb_stem()}られる"

    def causative_form(self):
        rule = "Attach させる to the verb stem"
        return rule, f"{self.verb_stem()}させる"

    def causative_passive_form(self):
        rule = "Attach させられる to the verb stem"
        return rule, f"{self.verb_stem()}させられる"


class IrregularVerbs(Verbs):
    verb_type = "Irregular"

    def te_form(self):
        rule = "Replace the stem with the corresponding い kana, then add て"
        return rule, f"{self.verb_stem('い')}て"

    def verb_stem(self, ending="い"):
        return godan_transformation[self.stem][ending]

    def negative_te_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add ないで"
            return rule, f"{self.verb_stem('い')}ないで"
        else:
            rule = "Replace the stem with the corresponding お kana, then add ないで"
            return rule, f"{self.verb_stem('お')}ないで"

    def masu_form(self):
        rule = "Replace the stem with the corresponding い kana, then add ます"
        return rule, f"{self.verb_stem('い')}ます"

    def masen_form(self):
        rule = "Replace the stem with the corresponding い kana, then add ません"
        return rule, f"{self.verb_stem('い')}ません"

    def mashita_form(self):
        rule = "Replace the stem with the corresponding い kana, then add ました"
        return rule, f"{self.verb_stem('い')}ました"

    def masendeshita_form(self):
        rule = "Replace the stem with the corresponding い kana, then add ませんでした"
        return rule, f"{self.verb_stem('い')}ませんでした"

    def dictionary_form(self):
        rule = "Add る to the verb stem"
        return rule, self.verb

    def nai_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add ない"
            return rule, f"{self.verb_stem('い')}ない"
        else:
            rule = "Replace the stem with the corresponding お kana, then add ない"
            return rule, f"{self.verb_stem('お')}ない"

    def ta_form(self):
        rule = "Replace the stem with the corresponding い kana, then add た"
        return rule, f"{self.verb_stem('い')}た"

    def nakatta_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add なかった"
            return rule, f"{self.verb_stem('い')}なかった"
        else:
            rule = "Replace the stem with the corresponding お kana, then add なかった"
            return rule, f"{self.verb_stem('お')}なかった"

    def ba_form(self):
        if self.stem == "す":
            rule = "Add れば to the verb stem"
            return rule, f"{self.stem}れば"
        else:
            rule = "Replace the stem with the corresponding お kana, then add れば"
            return rule, f"{self.verb_stem('お')}れば"

    def negative_ba_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add なければ"
            return rule, f"{self.verb_stem('い')}なければ"
        else:
            rule = "Replace the stem with the corresponding お kana, then add なければ"
            return rule, f"{self.verb_stem('お')}なければ"

    def tara_form(self):
        rule = "Replace the stem with the corresponding い kana, then add たら"
        return rule, f"{self.verb_stem('い')}たら"

    def negative_tara_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add なかったら"
            return rule, f"{self.verb_stem('い')}なかったら"
        else:
            rule = "Replace the stem with the corresponding お kana, then add なかったら"
            return rule, f"{self.verb_stem('お')}なかったら"

    def imperative_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add る"
            return rule, f"{self.verb_stem('い')}る"
        else:
            rule = "Replace with こい"
            return rule, "こい"

    def formal_imperative_form(self):
        rule = "Replace the stem with the corresponding い kana, then add なさい"
        return rule, f"{self.verb_stem('い')}なさい"

    def volitional_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding い kana, then add よう"
            return rule, f"{self.verb_stem('い')}よう"
        else:
            rule = "Replace the stem with the corresponding お kana, then add よう"
            return rule, f"{self.verb_stem('お')}よう"

    def formal_volitional_form(self):
        rule = "Replace the stem with the corresponding い kana, then add ましょう"
        return rule, f"{self.verb_stem('い')}ましょう"

    def potential_form(self):
        if self.stem == "す":
            rule = "Replace with できる"
            return rule, "できる"
        else:
            rule = "Replace the stem with the corresponding お kana, then add られる"
            return rule, f"{self.verb_stem('お')}られる"

    def passive_form(self):
        if self.stem == "す":
            rule = "Replace the stem with the corresponding あ kana, then add られる"
            return rule, f"{self.verb_stem('あ')}られる"
        else:
            rule = "Replace the stem with the corresponding お kana, then add られる"
            return rule, f"{self.verb_stem('お')}られる"

    def causative_form(self):
        if self.stem == "す":
            rule = "Replace with させる"
            return rule, "させる"
        else:
            rule = "Replace the stem with the corresponding お kana, then add させる"
            return rule, f"{self.verb_stem('お')}させる"

    def causative_passive_form(self):
        if self.stem == "す":
            rule = "Replace with させられる"
            return rule, "させられる"
        else:
            rule = "Replace the stem with the corresponding お kana, then add させられる"
            return rule, f"{self.verb_stem('お')}させられる"
