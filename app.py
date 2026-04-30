from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

YOUR_KINOPOISK_API_KEY = 'AVGM0J4-PSZ47T5-K7TTGN9-QDXQEQA'

KNOWN_MOVIES = {
    'шрек': {'id': 434, 'title': 'Шрек', 'alt_titles': ['Shrek']},
    'леон': {'id': 389, 'title': 'Леон', 'alt_titles': ['Leon', 'The Professional']},
    'зеленая книга': {'id': 512730, 'title': 'Зеленая книга', 'alt_titles': ['Green Book']},
    'джокер': {'id': 1143242, 'title': 'Джокер', 'alt_titles': ['Joker']},
    'интерстеллар': {'id': 258687, 'title': 'Интерстеллар', 'alt_titles': ['Interstellar']},
    'побег из шоушенка': {'id': 326, 'title': 'Побег из Шоушенка', 'alt_titles': ['The Shawshank Redemption']},
    'начало': {'id': 447301, 'title': 'Начало', 'alt_titles': ['Inception']},
    'матрица': {'id': 474, 'title': 'Матрица', 'alt_titles': ['The Matrix']},
    'форрест гамп': {'id': 626, 'title': 'Форрест Гамп', 'alt_titles': ['Forrest Gump']},
    'бойцовский клуб': {'id': 497, 'title': 'Бойцовский клуб', 'alt_titles': ['Fight Club']},
    'титаник': {'id': 595, 'title': 'Титаник', 'alt_titles': ['Titanic']},
    'властелин колец': {'id': 470, 'title': 'Властелин колец: Братство кольца', 'alt_titles': ['The Lord of the Rings: The Fellowship of the Ring']},
    'крестный отец': {'id': 560, 'title': 'Крестный отец', 'alt_titles': ['The Godfather']},
    'темный рыцарь': {'id': 155, 'title': 'Темный рыцарь', 'alt_titles': ['The Dark Knight']},
    'гладиатор': {'id': 594, 'title': 'Гладиатор', 'alt_titles': ['Gladiator']},
    'терминатор 2': {'id': 221, 'title': 'Терминатор 2: Судный день', 'alt_titles': ['Terminator 2: Judgment Day']},
    'назад в будущее': {'id': 187, 'title': 'Назад в будущее', 'alt_titles': ['Back to the Future']},
    'чужой': {'id': 134, 'title': 'Чужой', 'alt_titles': ['Alien']},
    'спасение рядового райана': {'id': 597, 'title': 'Спасти рядового Райана', 'alt_titles': ['Saving Private Ryan']},
    'пианист': {'id': 599, 'title': 'Пианист', 'alt_titles': ['The Pianist']},
    'отступники': {'id': 142, 'title': 'Отступники', 'alt_titles': ['The Departed']},
    'престиж': {'id': 1124, 'title': 'Престиж', 'alt_titles': ['The Prestige']},
    'молчание ягнят': {'id': 272, 'title': 'Молчание ягнят', 'alt_titles': ['The Silence of the Lambs']},
    'семь': {'id': 492, 'title': 'Семь', 'alt_titles': ['Se7en']},
    'город бога': {'id': 1040, 'title': 'Город Бога', 'alt_titles': ['City of God']},
    'жизнь прекрасна': {'id': 637, 'title': 'Жизнь прекрасна', 'alt_titles': ['Life Is Beautiful']},
    'зеленая миля': {'id': 601, 'title': 'Зеленая миля', 'alt_titles': ['The Green Mile']},
    'на игле': {'id': 537, 'title': 'На игле', 'alt_titles': ['Trainspotting']},
    'криминальное чтиво': {'id': 680, 'title': 'Криминальное чтиво', 'alt_titles': ['Pulp Fiction']},
    'хороший плохой злой': {'id': 429, 'title': 'Хороший, плохой, злой', 'alt_titles': ['The Good, the Bad and the Ugly']},
    'список шиндлера': {'id': 596, 'title': 'Список Шиндлера', 'alt_titles': ["Schindler's List"]},
    'аватар': {'id': 119, 'title': 'Аватар', 'alt_titles': ['Avatar']},
    'мстители': {'id': 293, 'title': 'Мстители', 'alt_titles': ['The Avengers']},
    'железный человек': {'id': 1924, 'title': 'Железный человек', 'alt_titles': ['Iron Man']},
    'человек паук': {'id': 300, 'title': 'Человек-паук', 'alt_titles': ['Spider-Man']},
    'бэтмен': {'id': 268, 'title': 'Бэтмен', 'alt_titles': ['Batman']},
    'супермен': {'id': 1929, 'title': 'Супермен', 'alt_titles': ['Superman']},
    'тор': {'id': 10195, 'title': 'Тор', 'alt_titles': ['Thor']},
    'стражи галактики': {'id': 260340, 'title': 'Стражи Галактики', 'alt_titles': ['Guardians of the Galaxy']},
    'черная пантера': {'id': 284216, 'title': 'Чёрная пантера', 'alt_titles': ['Black Panther']},
    'доктор стрэндж': {'id': 284052, 'title': 'Доктор Стрэндж', 'alt_titles': ['Doctor Strange']},
    'капитан америка': {'id': 17706, 'title': 'Первый мститель', 'alt_titles': ['Captain America: The First Avenger']},
    'гарри поттер': {'id': 671, 'title': 'Гарри Поттер и философский камень', 'alt_titles': ['Harry Potter and the Sorcerer Stone']},
    'властелин колец 2': {'id': 471, 'title': 'Властелин колец: Две крепости', 'alt_titles': ['The Lord of the Rings: The Two Towers']},
    'властелин колец 3': {'id': 472, 'title': 'Властелин колец: Возвращение короля', 'alt_titles': ['The Lord of the Rings: The Return of the King']},
    'хоббит': {'id': 49051, 'title': 'Хоббит: Нежданное путешествие', 'alt_titles': ['The Hobbit: An Unexpected Journey']},
    'звездные войны': {'id': 11, 'title': 'Звёздные войны. Эпизод 4: Новая надежда', 'alt_titles': ['Star Wars: Episode IV - A New Hope']},
    'империя наносит ответный удар': {'id': 1891, 'title': 'Звёздные войны. Эпизод 5: Империя наносит ответный удар', 'alt_titles': ['Star Wars: Episode V - The Empire Strikes Back']},
    'возвращение джедая': {'id': 1892, 'title': 'Звёздные войны. Эпизод 6: Возвращение джедая', 'alt_titles': ['Star Wars: Episode VI - Return of the Jedi']},
    'парк юрского периода': {'id': 329, 'title': 'Парк юрского периода', 'alt_titles': ['Jurassic Park']},
    'король лев': {'id': 8587, 'title': 'Король Лев', 'alt_titles': ['The Lion King']},
    'красавица и чудовище': {'id': 10020, 'title': 'Красавица и Чудовище', 'alt_titles': ['Beauty and the Beast']},
    'история игрушек': {'id': 862, 'title': 'История игрушек', 'alt_titles': ['Toy Story']},
    'тачки': {'id': 2062, 'title': 'Тачки', 'alt_titles': ['Cars']},
    'валли': {'id': 10681, 'title': 'ВАЛЛ·И', 'alt_titles': ['WALL·E']},
    'вверх': {'id': 14160, 'title': 'Вверх', 'alt_titles': ['Up']},
    'холодное сердце': {'id': 109445, 'title': 'Холодное сердце', 'alt_titles': ['Frozen']},
    'моана': {'id': 277834, 'title': 'Моана', 'alt_titles': ['Moana']},
    'зоотопия': {'id': 260513, 'title': 'Зверополис', 'alt_titles': ['Zootopia']},
    'суперсемейка': {'id': 9806, 'title': 'Суперсемейка', 'alt_titles': ['The Incredibles']},
    'рататуй': {'id': 2062, 'title': 'Рататуй', 'alt_titles': ['Ratatouille']},
    'покахонтас': {'id': 10528, 'title': 'Покахонтас', 'alt_titles': ['Pocahontas']},
    'мулан': {'id': 10681, 'title': 'Мулан', 'alt_titles': ['Mulan']},
    'алладдин': {'id': 812, 'title': 'Аладдин', 'alt_titles': ['Aladdin']},
    'русалочка': {'id': 11013, 'title': 'Русалочка', 'alt_titles': ['The Little Mermaid']},
    'красотка': {'id': 1648, 'title': 'Красотка', 'alt_titles': ['Pretty Woman']},
    'привидение': {'id': 10494, 'title': 'Привидение', 'alt_titles': ['Ghost']},
    'день сурка': {'id': 1366, 'title': 'День сурка', 'alt_titles': ['Groundhog Day']},
    'один дома': {'id': 771, 'title': 'Один дома', 'alt_titles': ['Home Alone']},
    'миссия невыполнима': {'id': 954, 'title': 'Миссия невыполнима', 'alt_titles': ['Mission: Impossible']},
    'крепкий орешек': {'id': 562, 'title': 'Крепкий орешек', 'alt_titles': ['Die Hard']},
    'скорость': {'id': 1648, 'title': 'Скорость', 'alt_titles': ['Speed']},
    'брат': {'id': 5952, 'title': 'Брат', 'alt_titles': ['Brother']},
    'брат 2': {'id': 5953, 'title': 'Брат 2', 'alt_titles': ['Brother 2']},
    'бой с тенью': {'id': 15373, 'title': 'Бой с тенью', 'alt_titles': ['Shadowboxing']},
    'ночной дозор': {'id': 11400, 'title': 'Ночной дозор', 'alt_titles': ['Night Watch']},
    'сталинград': {'id': 30912, 'title': 'Сталинград', 'alt_titles': ['Stalingrad']},
    'экипаж': {'id': 71895, 'title': 'Экипаж', 'alt_titles': ['The Crew']},
    'левиафан': {'id': 258516, 'title': 'Левиафан', 'alt_titles': ['Leviathan']},
    'дурак': {'id': 284053, 'title': 'Дурак', 'alt_titles': ['The Fool']},
    'иди и смотри': {'id': 2850, 'title': 'Иди и смотри', 'alt_titles': ['Come and See']},
    'сталкер': {'id': 2851, 'title': 'Сталкер', 'alt_titles': ['Stalker']},
    'солярис': {'id': 2852, 'title': 'Солярис', 'alt_titles': ['Solaris']},
    'зеркало': {'id': 2853, 'title': 'Зеркало', 'alt_titles': ['Mirror']},
    'андрей рублев': {'id': 2854, 'title': 'Андрей Рублёв', 'alt_titles': ['Andrei Rublev']},
    'война и мир': {'id': 2855, 'title': 'Война и мир', 'alt_titles': ['War and Peace']},
    'anna karenina': {'id': 2856, 'title': 'Анна Каренина', 'alt_titles': ['Anna Karenina']},
    'евгений онегин': {'id': 2857, 'title': 'Евгений Онегин', 'alt_titles': ['Eugene Onegin']},
    'герой нашего времени': {'id': 2858, 'title': 'Герой нашего времени', 'alt_titles': ['A Hero of Our Time']},
    'отцы и дети': {'id': 2859, 'title': 'Отцы и дети', 'alt_titles': ['Fathers and Sons']},
    'преступление и наказание': {'id': 2860, 'title': 'Преступление и наказание', 'alt_titles': ['Crime and Punishment']},
    'идиот': {'id': 2861, 'title': 'Идиот', 'alt_titles': ['The Idiot']},
    'бесы': {'id': 2862, 'title': 'Бесы', 'alt_titles': ['Demons']},
    'карамазовы': {'id': 2863, 'title': 'Братья Карамазовы', 'alt_titles': ['The Brothers Karamazov']},
    'мастер и маргарита': {'id': 2864, 'title': 'Мастер и Маргарита', 'alt_titles': ['The Master and Margarita']},
    'собачье сердце': {'id': 2865, 'title': 'Собачье сердце', 'alt_titles': ['Heart of a Dog']},
    'день опричника': {'id': 2866, 'title': 'День опричника', 'alt_titles': ['The Day of the Oprichnik']},
    'generation п': {'id': 2867, 'title': 'Generation П', 'alt_titles': ['Generation P']},
    'платонов': {'id': 2868, 'title': 'Платонов', 'alt_titles': ['Platonov']},
    'кысь': {'id': 2869, 'title': 'Кысь', 'alt_titles': ['The Lynx']},
    'метро 2033': {'id': 2870, 'title': 'Метро 2033', 'alt_titles': ['Metro 2033']},
    'обитаемый остров': {'id': 2871, 'title': 'Обитаемый остров', 'alt_titles': ['Inhabited Island']},
    'пикник на обочине': {'id': 2872, 'title': 'Пикник на обочине', 'alt_titles': ['Roadside Picnic']},
    'трудно быть богом': {'id': 2873, 'title': 'Трудно быть богом', 'alt_titles': ['Hard to Be a God']},
    'улитка на склоне': {'id': 2874, 'title': 'Улитка на склоне', 'alt_titles': ['Snail on the Slope']},
    'хищные вещи века': {'id': 2875, 'title': 'Хищные вещи века', 'alt_titles': ['Predatory Things of the Century']},
    'за миллиард лет до конца света': {'id': 2876, 'title': 'За миллиард лет до конца света', 'alt_titles': ['Definitely Maybe']},
    'понедельник начинается в субботу': {'id': 2877, 'title': 'Понедельник начинается в субботу', 'alt_titles': ['Monday Begins on Saturday']},
    'сказка о тройке': {'id': 2878, 'title': 'Сказка о Тройке', 'alt_titles': ['Tale of the Troika']},
    'град обреченный': {'id': 2879, 'title': 'Град обреченный', 'alt_titles': ['Doomed City']},
    'хромая судьба': {'id': 2880, 'title': 'Хромая судьба', 'alt_titles': ['Lame Fate']},
    'отель у погибшего альпиниста': {'id': 2881, 'title': 'Отель У Погибшего Альпиниста', 'alt_titles': ['Dead Mountaineers Hotel']},
    'волны гасят ветер': {'id': 2882, 'title': 'Волны гасят ветер', 'alt_titles': ['Waves Quench the Wind']},
    'мальчик и тьма': {'id': 2883, 'title': 'Мальчик и тьма', 'alt_titles': ['The Boy and the Darkness']},
    'дед мороз битва': {'id': 2884, 'title': 'Дед Мороз. Битва Магов', 'alt_titles': ['Ded Moroz. Battle of Mages']},
    'последний богатырь': {'id': 2885, 'title': 'Последний богатырь', 'alt_titles': ['The Last Bogatyr']},
    'холоп': {'id': 2886, 'title': 'Холоп', 'alt_titles': ['Kholop']},
    'движение вверх': {'id': 2887, 'title': 'Движение вверх', 'alt_titles': ['Going Vertical']},
    'экипаж 2016': {'id': 2888, 'title': 'Экипаж', 'alt_titles': ['The Crew 2016']},
    'дуэлянт': {'id': 2889, 'title': 'Дуэлянт', 'alt_titles': ['The Duelist']},
    'викинг': {'id': 2890, 'title': 'Викинг', 'alt_titles': ['Viking']},
    'фортросс': {'id': 2891, 'title': 'Форт Росс: В поисках приключений', 'alt_titles': ['Fort Ross: In Search of Adventures']},
    'батальон': {'id': 2892, 'title': 'Батальонъ', 'alt_titles': ['Battalion']},
    'белый тигр': {'id': 2893, 'title': 'Белый тигр', 'alt_titles': ['White Tiger']},
    'звезда': {'id': 2894, 'title': 'Звезда', 'alt_titles': ['The Star']},
    'кукушка': {'id': 2895, 'title': 'Кукушка', 'alt_titles': ['The Cuckoo']},
    '9 рота': {'id': 2896, 'title': '9 рота', 'alt_titles': ['The 9th Company']},
    'свои': {'id': 2897, 'title': 'Свои', 'alt_titles': ['Svoi']},
    'турецкий гамбит': {'id': 2898, 'title': 'Турецкий гамбит', 'alt_titles': ['Turkish Gambit']},
    'сталинград 2013': {'id': 2899, 'title': 'Сталинград', 'alt_titles': ['Stalingrad 2013']},
    'тарас бульба': {'id': 2900, 'title': 'Тарас Бульба', 'alt_titles': ['Taras Bulba']},
    'адмирал': {'id': 2901, 'title': 'Адмиралъ', 'alt_titles': ['Admiral']},
    'монгол': {'id': 2902, 'title': 'Монгол', 'alt_titles': ['Mongol']},
    'царь': {'id': 2903, 'title': 'Царь', 'alt_titles': ['Tsar']},
    'остров': {'id': 2904, 'title': 'Остров', 'alt_titles': ['The Island']},
    'покаяние': {'id': 2905, 'title': 'Покаяние', 'alt_titles': ['Repentance']},
    'восток-запад': {'id': 2906, 'title': 'Восток-Запад', 'alt_titles': ['East-West']},
    'сибирский цирюльник': {'id': 2907, 'title': 'Сибирский цирюльник', 'alt_titles': ['The Barber of Siberia']},
    'устой': {'id': 2908, 'title': 'Утомлённые солнцем', 'alt_titles': ['Burnt by the Sun']},
    'вор': {'id': 2909, 'title': 'Вор', 'alt_titles': ['The Thief']},
    'брат 3': {'id': 2910, 'title': 'Брат 3', 'alt_titles': ['Brother 3']},
    'бой с тенью 2': {'id': 2911, 'title': 'Бой с тенью 2: Реванш', 'alt_titles': ['Shadowboxing 2: Revenge']},
    'ночной дозор 2': {'id': 2912, 'title': 'Дневной дозор', 'alt_titles': ['Day Watch']},
    'дозоры': {'id': 2913, 'title': 'Дозоры', 'alt_titles': ['The Watches']},
    'обитаемый остров 2': {'id': 2914, 'title': 'Обитаемый остров: Схватка', 'alt_titles': ['Inhabited Island: Fight']},
    'мы из будущего': {'id': 2915, 'title': 'Мы из будущего', 'alt_titles': ['We Are from the Future']},
    'мы из будущего 2': {'id': 2916, 'title': 'Мы из будущего 2', 'alt_titles': ['We Are from the Future 2']},
    'сволочи': {'id': 2917, 'title': 'Сволочи', 'alt_titles': ['Scumbags']},
    'жара': {'id': 2918, 'title': 'Жара', 'alt_titles': ['Zhara']},
    'самый лучший фильм': {'id': 2919, 'title': 'Самый лучший фильм', 'alt_titles': ['The Best Movie']},
    'самый лучший фильм 2': {'id': 2920, 'title': 'Самый лучший фильм 2', 'alt_titles': ['The Best Movie 2']},
    'наша russia': {'id': 2921, 'title': 'Наша Russia. Яйца судьбы', 'alt_titles': ['Nasha Russia. Eggs of Fate']},
    'реальные пацаны': {'id': 2922, 'title': 'Реальные пацаны против зомби', 'alt_titles': ['Real Guys vs Zombies']},
    'чемпионы': {'id': 2923, 'title': 'Чемпионы', 'alt_titles': ['Champions']},
    'чемпионы 2': {'id': 2924, 'title': 'Чемпионы: Быстрее. Выше. Сильнее', 'alt_titles': ['Champions 2']},
    'лед': {'id': 2925, 'title': 'Лёд', 'alt_titles': ['Ice']},
    'лед 2': {'id': 2926, 'title': 'Лёд 2', 'alt_titles': ['Ice 2']},
    'текст': {'id': 2927, 'title': 'Текст', 'alt_titles': ['Text']},
    'бык': {'id': 2928, 'title': 'Бык', 'alt_titles': ['Bull']},
    'дау': {'id': 2929, 'title': 'Дау', 'alt_titles': ['DAU']},
    'дау наталья': {'id': 2930, 'title': 'Дау. Наталья', 'alt_titles': ['DAU. Natasha']},
    'дау дегенерация': {'id': 2931, 'title': 'Дау. Дегенерация', 'alt_titles': ['DAU. Degeneration']},
    'француз': {'id': 2932, 'title': 'Француз', 'alt_titles': ['The French']},
    'одесса': {'id': 2933, 'title': 'Одесса', 'alt_titles': ['Odessa']},
    'подольские курсанты': {'id': 2934, 'title': 'Подольские курсанты', 'alt_titles': ['Podolsk Cadets']},
    'калитинский мост': {'id': 2935, 'title': 'Калитинский мост', 'alt_titles': ['Kalitinsky Bridge']},
    'серебряные коньки': {'id': 2936, 'title': 'Серебряные коньки', 'alt_titles': ['Silver Skates']},
    'огонь': {'id': 2937, 'title': 'Огонь', 'alt_titles': ['Fire']},
    'вратарь галактики': {'id': 2938, 'title': 'Вратарь Галактики', 'alt_titles': ['Goalkeeper of the Galaxy']},
    'кома': {'id': 2939, 'title': 'Кома', 'alt_titles': ['Coma']},
    'спутник': {'id': 2940, 'title': 'Спутник', 'alt_titles': ['Sputnik']},
    'коллапс': {'id': 2941, 'title': 'Коллапс', 'alt_titles': ['Collapse']},
    'вторжение': {'id': 2942, 'title': 'Вторжение', 'alt_titles': ['Invasion']},
    'притяжение': {'id': 2943, 'title': 'Притяжение', 'alt_titles': ['Attraction']},
    'притяжение 2': {'id': 2944, 'title': 'Притяжение 2', 'alt_titles': ['Attraction 2']},
    'гоголь': {'id': 2945, 'title': 'Гоголь. Начало', 'alt_titles': ['Gogol. The Beginning']},
    'гоголь вий': {'id': 2946, 'title': 'Гоголь. Вий', 'alt_titles': ['Gogol. Viy']},
    'гоголь страшная месть': {'id': 2947, 'title': 'Гоголь. Страшная месть', 'alt_titles': ['Gogol. Terrible Vengeance']},
    'он дракон': {'id': 2948, 'title': 'Он - дракон', 'alt_titles': ['He is a Dragon']},
    'дух': {'id': 2949, 'title': 'Дух', 'alt_titles': ['Spirit']},
    'ночной продавец': {'id': 2950, 'title': 'Ночной продавец', 'alt_titles': ['Night Seller']}
}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    my_items = db.relationship('MyItem', backref='this_user', lazy=True, cascade='all, delete-orphan')

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()

class MyItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(100), default='Неизвестно')
    description = db.Column(db.Text, default='')
    kinopoisk_rating = db.Column(db.String(20), default='Нет рейтинга')
    year = db.Column(db.String(20))
    how_its_going = db.Column(db.String(50), default='plan')
    my_rating = db.Column(db.Integer, nullable=True)
    user_who_owns = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_when_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_watched = db.Column(db.DateTime)
    watch_count = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default='')
    director = db.Column(db.String(150))
    duration = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'year': self.year,
            'genre': self.genre,
            'rating': self.kinopoisk_rating,
            'my_rating': self.my_rating,
            'status': self.how_its_going,
            'watch_count': self.watch_count,
            'created_at': self.date_when_created.strftime('%Y-%m-%d') if self.date_when_created else None
        }

@login_manager.user_loader
def load_this_user(user_id):
    return User.query.get(int(user_id))

def search_movies_kinopoisk(query):
    try:
        query_lower = query.strip().lower()
        if len(query_lower) < 2:
            return []
        for known_key, known_movie in KNOWN_MOVIES.items():
            if query_lower in known_key or query_lower in [t.lower() for t in known_movie['alt_titles']]:
                details = get_movie_details_kinopoisk(known_movie['id'])
                if details:
                    return [{
                        'id': known_movie['id'],
                        'title': known_movie['title'],
                        'year': details.get('year', ''),
                        'rating': details.get('rating', 'Нет рейтинга')
                    }]
                else:
                    return [{
                        'id': known_movie['id'],
                        'title': known_movie['title'],
                        'year': '',
                        'rating': 'Нет рейтинга'
                    }]
        url = "https://api.kinopoisk.dev/v1.4/movie/search"
        headers = {
            'X-API-KEY': YOUR_KINOPOISK_API_KEY,
            'Content-Type': 'application/json'
        }
        params = {
            'query': query_lower,
            'limit': 30
        }
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            movies = []
            for movie in data.get('docs', []):
                name_ru = movie.get('name') or ''
                name_alt = movie.get('alternativeName') or ''
                name_en = movie.get('enName') or ''
                if (query_lower in name_ru.lower() or
                        query_lower in name_alt.lower() or
                        query_lower in name_en.lower()):
                    title = name_ru or name_alt or name_en or 'Без названия'
                    movies.append({
                        'id': movie.get('id'),
                        'title': title,
                        'year': movie.get('year', ''),
                        'rating': movie.get('rating', {}).get('kp', 'Нет рейтинга')
                    })
            seen = set()
            unique_movies = []
            for movie in movies:
                if movie['id'] not in seen:
                    seen.add(movie['id'])
                    unique_movies.append(movie)
            return unique_movies
        else:
            return []
    except Exception:
        return []

def get_movie_details_kinopoisk(movie_id):
    try:
        url = f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}"
        headers = {
            'X-API-KEY': YOUR_KINOPOISK_API_KEY,
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            title = data.get('name') or data.get('alternativeName') or data.get('enName') or 'Без названия'
            year = data.get('year', '')
            genres = [genre.get('name', '') for genre in data.get('genres', [])]
            genre_str = ', '.join(genres) if genres else 'Неизвестно'
            rating_data = data.get('rating', {})
            rating = rating_data.get('kp') or rating_data.get('imdb') or 'Нет рейтинга'
            if isinstance(rating, (int, float)):
                rating = f"{rating:.1f}"
            description = data.get('description') or data.get('shortDescription') or 'Описание не найдено'
            director = ''
            if data.get('director'):
                director = ', '.join(data.get('director', []))
            duration = data.get('movieLength', 0)
            return {
                'title': title,
                'year': str(year) if year else '',
                'genre': genre_str,
                'rating': str(rating),
                'description': description,
                'director': director,
                'duration': duration
            }
        else:
            return None
    except Exception:
        return None

@app.route('/')
@login_required
def index():
    all_my_items = MyItem.query.filter_by(user_who_owns=current_user.id).order_by(MyItem.date_when_created.desc()).all()
    planned = sum(1 for item in all_my_items if item.how_its_going == 'plan')
    watching = sum(1 for item in all_my_items if item.how_its_going == 'watching')
    completed = sum(1 for item in all_my_items if item.how_its_going == 'completed')
    ratings = [item.my_rating for item in all_my_items if item.my_rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    return render_template('index.html',
                           items=all_my_items,
                           planned=planned,
                           watching=watching,
                           completed=completed,
                           avg_rating=round(avg_rating, 1))

@app.route('/search_movies')
def search_movies():
    query = request.args.get('query', '').strip()
    if len(query) < 2:
        return jsonify([])
    movies = search_movies_kinopoisk(query)
    return jsonify(movies)

@app.route('/get_movie_details')
def get_movie_details_route():
    movie_id = request.args.get('id', '')
    if not movie_id:
        return jsonify({'error': 'No ID provided'}), 400
    details = get_movie_details_kinopoisk(movie_id)
    if details:
        return jsonify(details)
    return jsonify({'error': 'Not found'}), 404

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username_from_form = request.form.get('username')
        email_from_form = request.form.get('email')
        password_from_form = request.form.get('password')
        confirm_password_from_form = request.form.get('confirm_password')
        if not username_from_form or not email_from_form or not password_from_form:
            flash('Заполни все поля!', 'danger')
            return redirect(url_for('register'))
        if password_from_form != confirm_password_from_form:
            flash('Пароли не совпадают!', 'danger')
            return redirect(url_for('register'))
        user_with_same_email = User.query.filter_by(email=email_from_form).first()
        if user_with_same_email:
            flash('Такой email уже есть в системе', 'danger')
            return redirect(url_for('register'))
        user_with_same_username = User.query.filter_by(username=username_from_form).first()
        if user_with_same_username:
            flash('Такое имя уже занято', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password_from_form, method='pbkdf2:sha256')
        new_user = User(username=username_from_form, email=email_from_form, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Ты зарегистрировался! Теперь войди', 'success')
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            flash('Что-то пошло не так', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email_from_form = request.form.get('email')
        password_from_form = request.form.get('password')
        remember_me = request.form.get('remember')
        my_user = User.query.filter_by(email=email_from_form).first()
        if my_user:
            password_is_correct = check_password_hash(my_user.password, password_from_form)
            if password_is_correct:
                login_user(my_user, remember=bool(remember_me))
                my_user.update_last_login()
                flash('Привет, ' + my_user.username + '!', 'success')
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
            else:
                flash('Неверный пароль', 'danger')
        else:
            flash('Пользователь с таким email не найден', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ты вышел из аккаунта', 'info')
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        selected_id = request.form.get('selected_id')
        if not selected_id:
            flash('Выбери фильм из списка!', 'danger')
            return redirect(url_for('add_item'))
        movie_data = get_movie_details_kinopoisk(selected_id)
        if movie_
            existing = MyItem.query.filter_by(
                name=movie_data['title'],
                user_who_owns=current_user.id
            ).first()
            if existing:
                flash(f'Фильм "{movie_data["title"]}" уже есть в вашем списке!', 'warning')
                return redirect(url_for('index'))
            new_item = MyItem(
                name=movie_data['title'],
                genre=movie_data['genre'],
                description=movie_data['description'],
                kinopoisk_rating=movie_data['rating'],
                year=movie_data['year'],
                how_its_going='plan',
                user_who_owns=current_user.id,
                director=movie_data.get('director', ''),
                duration=movie_data.get('duration', 0)
            )
            db.session.add(new_item)
            db.session.commit()
            flash(f'✅ Фильм "{movie_data["title"]}" добавлен! Рейтинг КП: {movie_data["rating"]}', 'success')
        else:
            flash('❌ Не удалось загрузить информацию о фильме', 'danger')
        return redirect(url_for('index'))
    return render_template('add_item.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item_to_edit = MyItem.query.get_or_404(id)
    if item_to_edit.user_who_owns != current_user.id:
        flash('Это не твой элемент!', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        status_from_form = request.form.get('status')
        rating_from_form = request.form.get('rating')
        notes_from_form = request.form.get('notes')
        watch_count = request.form.get('watch_count')
        if status_from_form:
            item_to_edit.how_its_going = status_from_form
            if status_from_form == 'completed' and not item_to_edit.date_watched:
                item_to_edit.date_watched = datetime.utcnow()
        if rating_from_form and rating_from_form.isdigit():
            item_to_edit.my_rating = int(rating_from_form)
        if notes_from_form is not None:
            item_to_edit.notes = notes_from_form
        if watch_count and watch_count.isdigit():
            item_to_edit.watch_count = int(watch_count)
        db.session.commit()
        flash('Изменения сохранены!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_item.html', item=item_to_edit)

@app.route('/delete/<int:id>')
@login_required
def delete_item(id):
    item_to_delete = MyItem.query.get_or_404(id)
    if item_to_delete.user_who_owns == current_user.id:
        db.session.delete(item_to_delete)
        db.session.commit()
        flash('Удалено!', 'success')
    else:
        flash('Нельзя удалить чужое!', 'danger')
    return redirect(url_for('index'))

@app.route('/export/json')
@login_required
def export_json():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()
    data = []
    for item in items:
        data.append({
            'name': item.name,
            'year': item.year,
            'genre': item.genre,
            'kinopoisk_rating': item.kinopoisk_rating,
            'my_rating': item.my_rating,
            'status': item.how_its_going,
            'description': item.description,
            'director': item.director,
            'duration': item.duration,
            'watch_count': item.watch_count,
            'notes': item.notes,
            'date_added': item.date_when_created.strftime('%Y-%m-%d') if item.date_when_created else '',
            'date_watched': item.date_watched.strftime('%Y-%m-%d') if item.date_watched else ''
        })
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    response = make_response(json_text)
    response.headers["Content-Disposition"] = "attachment; filename=my_films.json"
    response.headers["Content-type"] = "application/json"
    return response

@app.route('/export/csv')
@login_required
def export_csv():
    items = MyItem.query.filter_by(user_who_owns=current_user.id).all()
    csv_lines = []
    csv_lines.append('Название,Год,Жанр,Рейтинг КП,Моя оценка,Статус,Описание,Режиссёр,Длительность,Просмотров,Заметки')
    for item in items:
        name = item.name if item.name else ''
        year = item.year if item.year else ''
        genre = item.genre if item.genre else ''
        rating = item.kinopoisk_rating if item.kinopoisk_rating else ''
        my_rating = str(item.my_rating) if item.my_rating else ''
        status = ''
        if item.how_its_going == 'plan':
            status = 'В планах'
        elif item.how_its_going == 'watching':
            status = 'Смотрю'
        else:
            status = 'Просмотрено'
        description = item.description if item.description else ''
        director = item.director if item.director else ''
        duration = str(item.duration) if item.duration else ''
        watch_count = str(item.watch_count) if item.watch_count else '0'
        notes = item.notes if item.notes else ''
        description = description.replace(',', ';').replace('\n', ' ').replace('"', "'")
        notes = notes.replace(',', ';').replace('\n', ' ').replace('"', "'")
        line = f'{name},{year},{genre},{rating},{my_rating},{status},{description},{director},{duration},{watch_count},{notes}'
        csv_lines.append(line)
    csv_text = '\n'.join(csv_lines)
    response = make_response(csv_text)
    response.headers["Content-Disposition"] = "attachment; filename=my_films.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
