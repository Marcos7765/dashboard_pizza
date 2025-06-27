import os
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import numpy as np

def list_png_files(folder_path):
    png_files = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".png"):
            png_files.append(filename)
    return png_files

image_pool = list_png_files("pizza_images")

def polar_mask(angle_size, _angle_offset, total_height, total_width):
    mask = np.zeros((total_height, total_width), np.uint8)
    angle_offset = _angle_offset
    for i in range(total_height):
        for j in range(total_width):
            point_angle = np.arctan2(i - total_height / 2, -j + total_width / 2) + np.pi
            if point_angle >= angle_offset and point_angle <= angle_offset + angle_size:
                mask[i, j] = 255
    return PIL.Image.fromarray(mask)

def slice_pizza(pizza_path, angle_size, angle_offset, base_scale = 1.):
    pizza = PIL.Image.open(pizza_path).convert("RGBA")
    if base_scale != 1.: 
        pizza = pizza.resize((int(pizza.width*base_scale), int(pizza.height*base_scale)))
    mask = polar_mask(angle_size, angle_offset, pizza.height, pizza.width).convert("1")
    a = pizza.getchannel('A').convert("1")
    pizza.putalpha(PIL.ImageChops.logical_and(mask, a))
    return pizza

def scale_to_angle(value, min_value, max_value):
    return 2*np.pi* (value - min_value) / (max_value - min_value)

def rotate_point(radius, angle, center_x, center_y):
    x = center_x + radius * np.cos(angle)
    y = center_y - radius * np.sin(angle)
    return x, y

def label_info(label:str, value, total):
    return f"{label}\n{value}\n({value/total*100:.2f}%)"

def pizza_plot(labels, values, image_pool=image_pool, base_scale=1., extended_ratio:float=1.5):

    norm_val = sum(values)
    angle_offset = 0
    angle_size = scale_to_angle(values[0], 0, norm_val)

    label_msg = label_info(labels[0], values[0], norm_val)
    base = slice_pizza(f"pizza_images/{image_pool[0]}", angle_size, angle_offset,
        base_scale=base_scale)
    extended_image = PIL.Image.new("RGBA",
        (int(base.width*extended_ratio), int(base.height*extended_ratio)),
        (0, 0, 0, 0)
    )

    print("Teste? ",int(base.width*extended_ratio), int(base.height*extended_ratio))

    center_offset = (int((extended_image.width - base.width) / 2), int((extended_image.height - base.height) / 2))
    text_radius = min(center_offset)/2 + base.width/2
    pizza_center = (center_offset[0] + base.width/2, center_offset[1] + base.height/2)
    extended_image.paste(base, center_offset)
    base = extended_image
    draw = PIL.ImageDraw.Draw(base)

    def draw_info(angle, info):
        text_pos = rotate_point(text_radius, angle, *pizza_center)
        text_anchor = "m" + ("d" if text_pos[1] > pizza_center[1] else "a")
        draw.text(
            text_pos, info, (0, 0, 0), anchor=text_anchor,
            font=PIL.ImageFont.load_default(text_radius/10), align="center",
            stroke_width=max(int(text_radius/200),1), stroke_fill=(255, 255, 255)
        )

    draw_info_stack = [(angle_offset + angle_size/2, label_msg)]

    angle_offset += angle_size
    for i, (label, value) in enumerate(zip(labels[1:], values[1:]), 1):
        label_msg = label_info(label, value, norm_val)
        angle_size = scale_to_angle(value, 0, norm_val)
        new_slice = slice_pizza(f"pizza_images/{image_pool[i]}", angle_size, angle_offset,
            base_scale=base_scale)
        base.paste(new_slice, center_offset, new_slice)
        center_angle = angle_offset + angle_size/2
        angle_offset += angle_size
        draw_info_stack.append((center_angle, label_msg))

    for args in draw_info_stack:
        draw_info(*args)

    return base

#print('Exemplo para pizza_plot(["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"], [1,1,1,1,1,2,3]).resize((500,500))')
#image:PIL.Image.Image = pizza_plot(["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"], [1,1,1,1,1, 2, 3]).resize((500,500))
#
#image.show()