import aiohttp
import datetime
import os
from shutil import copyfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

base_path = "images/banner/base"
tmp_path = "images/banner/tmp"
whitneyMedium = "/usr/share/fonts/whitney-medium.ttf"
whitneyBold = "/usr/share/fonts/whitney-bold.ttf"
header_height = 125
canvas_height = 145
upper_banner_image = "{}/upper_banner_image".format(base_path)
lower_banner_image = "{}/lower_banner_image.png".format(base_path)


async def create_banner(member, image_title, data):
    """Creates a banner based on the options passed
    Paramaters:
        member -> The user to display stats about
        image_title -> The title that will displayed before the stats
        data -> A dictionary that will be displayed, in the format 'Key: Value' like normal dictionaries"""
    # First ensure the paths we need are created
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(tmp_path, exist_ok=True)
    offset = 125

    # Open up the avatar, save it as a temporary file
    avatar_url = member.avatar_url
    avatar_path = "{}/avatar_{}_{}.png".format(tmp_path, member.id, int(datetime.datetime.utcnow().timestamp()))
    # Ensure the user has an avatar
    if avatar_url != "":
        with aiohttp.ClientSession() as s:
            async with s.get(avatar_url) as r:
                val = await r.read()
                with open(avatar_path, "wb") as f:
                    f.write(val)
    # Otherwise use the default avatar
    else:
        avatar_src_path = "{}/default_avatar.png".format(base_path)
        copyfile(avatar_src_path, avatar_path)

    # Parse the data we need to create our image
    username = (member.display_name[:23] + '...') if len(member.display_name) > 23 else member.display_name
    # Our data will be a list of tuples, so this is how we can get the keys and values we want
    result_keys = [k for k, v in data]
    result_values = [v for k, v in data]
    lines_of_text = len(result_keys)
    output_file = "{}/banner_{}_{}.jpg".format(tmp_path, member.id, int(datetime.datetime.utcnow().timestamp()))
    base_height = canvas_height + (lines_of_text * 20)

    # This is the background to the avatar
    mask = Image.open('{}/avatar_mask_220.png'.format(base_path)).convert('L')
    user_avatar = Image.open(avatar_path)
    output = ImageOps.fit(user_avatar, (110,110), centering=(0.5, 0.5))
    output.putalpha(mask)

    # Here's our finalized avatar image that we'll use
    avatar = output.resize((100, 100), Image.ANTIALIAS)

    # Now lets piece together the full image we'll use
    base_image = Image.new("RGB", (350, base_height), "#000000")

    # Create the header, including our avatar image with it
    header_top = Image.open(upper_banner_image).convert("RGBA")
    header_bot = Image.open(lower_banner_image).convert("RGBA")
    header_base_image = Image.new("RGB", (350, header_height), "#000000")
    header_base_image.paste(header_top, (0, 0), header_top)
    header_base_image.paste(header_bot, (0, 0), header_bot)
    header_base_image.paste(header_top, (0, 0), header_top)
    header_base_image.paste(avatar, (0, 8), avatar)

    # Place the username next to the avatar image
    h_b = Image.new('RGBA', (1050, 375)).convert("RGBA")
    draw_username_text = ImageDraw.Draw(h_b)
    font = ImageFont.truetype(whitneyMedium, 60)
    draw_username_text.text((300, 230), username, (255, 255, 255), font=font)
    username_text = h_b.resize((350, 125), Image.ANTIALIAS)
    header_base_image.paste(username_text, (0, 0), username_text)
    header = header_base_image.convert("RGBA")

    # Place the title in the image
    title = Image.new("RGB", (1050, 60), "#36393e").convert("RGBA")
    draw = ImageDraw.Draw(title)
    font = ImageFont.truetype(whitneyBold, 51)
    draw.text((375, -2), image_title, (255, 255, 255), font=font)
    mod_title = title.resize((350, 20), Image.ANTIALIAS)
    base_image.paste(mod_title, (0, offset), mod_title)

    # Loop through and place all the data in the image
    for current_line in range(lines_of_text):
        font = ImageFont.truetype(whitneyMedium, 96)
        text_bar = Image.new("RGB", (2100, 120), "#36393e").convert("RGBA")
        draw = ImageDraw.Draw(text_bar)
        text = "{}: ".format(result_keys[current_line])
        stat_text = "{}".format(result_values[current_line])
        stat_offset = draw.textsize(text, font=font, spacing=0)

        font = ImageFont.truetype(whitneyMedium, 96)
        draw.text((360, -4), text, (255, 255, 255), font=font, align="center")
        draw.text((360 + stat_offset[0], -4), stat_text, (0, 402, 504), font=font)
        save_me = text_bar.resize((350, 20), Image.ANTIALIAS)
        offset += 20
        base_image.paste(save_me, (0, offset), save_me)
    base_image.paste(header, (0, 0), header)
    base_image.save(output_file)

    os.remove(avatar_path)

    return output_file
