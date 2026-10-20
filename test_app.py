from PIL import Image
from hello import swap_halves

def test_swap_halves_lr():
    # Создаем тестовую картинку 10x10, левая половина красная, правая - синяя
    img = Image.new("RGB", (10, 10), "red")
    for x in range(5, 10):
        for y in range(10):
            img.putpixel((x, y), (0, 0, 255))
            
    result = swap_halves(img, "lr")
    
    # Проверяем, что левый верхний пиксель стал синим (поменялся местами)
    assert result.getpixel((0, 0)) == (0, 0, 255)
    # Проверяем, что правый верхний пиксель стал красным
    assert result.getpixel((9, 0)) == (255, 0, 0)

def test_swap_halves_tb():
    # Создаем картинку, верх - зеленый, низ - черный
    img = Image.new("RGB", (10, 10), "green")
    for x in range(10):
        for y in range(5, 10):
            img.putpixel((x, y), (0, 0, 0))
            
    result = swap_halves(img, "tb")
    
    # Проверяем, что верх стал черным, а низ - зеленым
    assert result.getpixel((0, 0)) == (0, 0, 0)
    assert result.getpixel((0, 9)) == (0, 128, 0)
