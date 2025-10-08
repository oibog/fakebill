import logging
import os
import io
import uuid
import requests
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from telegram import Update, ForceReply, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, ApplicationBuilder

codebyzpxdev = "assets"
OUTPUT_DIR = "output"
os.makedirs(codebyzpxdev, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEMPLATE_FRONT = os.path.join(codebyzpxdev, "cccd_mat_truoc.png")

FONT_ROBOTO_BOLD = os.path.join(codebyzpxdev, "Roboto-Bold.ttf")
FONT_ROBOTO_REGULAR = os.path.join(codebyzpxdev, "Roboto-Regular.ttf")
DEFAULT_AVATAR = os.path.join(codebyzpxdev, "avatar.png")

TEXT_COLOR_FRONT = (39, 39, 39)

DULIEDATAZPXDEV = {
    'socccd':       {'pos': (906, 1233), 'font_path': FONT_ROBOTO_BOLD, 'size': 61},
    'hovaten':      {'pos': (753, 1363), 'font_path': FONT_ROBOTO_REGULAR, 'size': 48},
    'ngaysinh':     {'pos': (1187, 1427), 'font_path': FONT_ROBOTO_REGULAR, 'size': 45},
    'gioitinh':     {'pos': (1027, 1490), 'font_path': FONT_ROBOTO_REGULAR, 'size': 40},
    'quoctich':     {'pos': (1560, 1482), 'font_path': FONT_ROBOTO_REGULAR, 'size': 44},
    'quequan':      {'pos': (753, 1605), 'font_path': FONT_ROBOTO_REGULAR, 'size': 44},
    'ngayhethan':   {'pos': (523, 1697), 'font_path': FONT_ROBOTO_REGULAR, 'size': 35, 'color': (32, 46, 39)},
    'thuongtru':    {'pos': (753, 1700), 'font_path': FONT_ROBOTO_REGULAR, 'size': 44},
}

AVATAR_POS = (327, 1161)
AVATAR_SIZE = (376, 512)

QR_POS = (1540, 890)
QR_SIZE = (222, 222)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def is_valid_date(date_str):
    try:
        datetime.strptime(date_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def create_cccd_front(data):
    try:
        if not os.path.exists(TEMPLATE_FRONT):
            logger.error(f"File phôi ảnh mặt trước không tìm thấy: {TEMPLATE_FRONT}")
            return None
        
        template = Image.open(TEMPLATE_FRONT).convert("RGBA")
        draw = ImageDraw.Draw(template)

        local_avatar_path = data.get('avatar', '')
        if local_avatar_path and os.path.exists(local_avatar_path):
            avatar = Image.open(local_avatar_path).convert("RGBA")
            avatar = avatar.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)
            template.paste(avatar, AVATAR_POS, avatar)
        elif os.path.exists(DEFAULT_AVATAR):
            default_avatar_img = Image.open(DEFAULT_AVATAR).convert("RGBA")
            default_avatar_img = default_avatar_img.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)
            template.paste(default_avatar_img, AVATAR_POS, default_avatar_img)
            logger.warning(f"Không tìm thấy ảnh chân dung tại '{local_avatar_path}', sử dụng ảnh mặc định.")
        else:
            logger.warning(f"Không tìm thấy ảnh chân dung tại '{local_avatar_path}' và không có ảnh mặc định '{DEFAULT_AVATAR}'.")

        qrcode_socccd = data.get('socccd', '000000000000')
        qrcode_hovaten = data.get('hovaten', 'UNKNOWN')
        qrcode_ngaysinh_raw = data.get('ngaysinh', '01/01/1900')
        qrcode_ngaysinh = qrcode_ngaysinh_raw.replace('/', '') if is_valid_date(qrcode_ngaysinh_raw) else '01011900'
        qrcode_gioitinh = data.get('gioitinh', 'Khac')
        qrcode_thuongtru = data.get('thuongtru', 'UNKNOWN')
        qrcode_ngayhethan_raw = data.get('ngayhethan', '01/01/2099')
        qrcode_ngayhethan = qrcode_ngayhethan_raw.replace('/', '') if is_valid_date(qrcode_ngayhethan_raw) else '01012099'

        qrcode_text = f"{qrcode_socccd}|{str(uuid.uuid4().int)[:9]}|{qrcode_hovaten}|{qrcode_ngaysinh}|{qrcode_gioitinh}|{qrcode_thuongtru}|{qrcode_ngayhethan}"
        qr_url = f"https://quickchart.io/qr?text={qrcode_text}&light=0000&ecLevel=H&format=png&size=700"
        
        try:
            qr_response = requests.get(qr_url, timeout=10)
            qr_response.raise_for_status()
            qr_image = Image.open(io.BytesIO(qr_response.content)).convert("RGBA")
            qr_image = qr_image.resize(QR_SIZE, Image.Resampling.LANCZOS)
            template.paste(qr_image, QR_POS, qr_image)
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi: Không thể tạo hoặc tải QR code. Lỗi: {e}")

        for key, config in DULIEDATAZPXDEV.items():
            text = data.get(key, "")
            if not os.path.exists(config['font_path']):
                logger.error(f"Lỗi: Không tìm thấy file font '{config['font_path']}'. Bỏ qua việc vẽ chữ cho '{key}'.")
                continue
            font = ImageFont.truetype(config['font_path'], config['size'])
            color = config.get('color', TEXT_COLOR_FRONT)
            
            if key == 'thuongtru':
                lines = []
                words = text.split(' ')
                current_line = ""
                max_chars = 40
                for word in words:
                    if len(current_line + " " + word) <= max_chars:
                        current_line += " " + word
                    else:
                        lines.append(current_line.strip())
                        current_line = word
                lines.append(current_line.strip())

                y_pos = config['pos'][1]
                for line in lines:
                    draw.text((config['pos'][0], y_pos), line, font=font, fill=color)
                    y_pos += config['size'] + 10
            else:
                draw.text(config['pos'], text, font=font, fill=color)

        output_buffer = io.BytesIO()
        template.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        return output_buffer

    except FileNotFoundError as e:
        logger.error(f"Lỗi FileNotFoundError trong create_cccd_front: {e}")
        return None
    except Exception as e:
        logger.error(f"Đã xảy ra lỗi không xác định trong create_cccd_front: {e}", exc_info=True)
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Chào {user.mention_html()}! Tôi là bot tạo ảnh Căn cước công dân.\n"
        "Để tạo ảnh, bạn cần **reply vào một ảnh** (làm ảnh chân dung) và dùng lệnh:\n"
        "<code>/cccd Họ và Tên | Ngày sinh | Giới tính | Quốc tịch | Quê quán | Nơi thường trú | Số CCCD | Ngày hết hạn</code>\n\n"
        "<b>Ví dụ:</b>\n"
        "<code>/cccd NGUYỄN VĂN A | 01/01/1990 | Nam | Việt Nam | Xã A, Huyện B, Tỉnh C | Số nhà X, Đường Y, Tỉnh Z | 001090123456 | 01/01/2090</code>\n\n"
        "Lưu ý: Bạn phải trả lời (reply) vào một ảnh để ảnh đó được dùng làm ảnh chân dung.",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Để tạo ảnh CCCD, reply vào một ảnh và dùng lệnh:\n"
        "<code>/cccd Họ và Tên | Ngày sinh | Giới tính | Quốc tịch | Quê quán | Nơi thường trú | Số CCCD | Ngày hết hạn</code>\n"
        "Ví dụ: <code>/cccd NGUYỄN VĂN A | 01/01/1990 | Nam | Việt Nam | Xã A, Huyện B, Tỉnh C | Số nhà X, Đường Y, Tỉnh Z | 001090123456 | 01/01/2090</code>",
        parse_mode='HTML'
    )

async def cccd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message
    
    if not user_message.reply_to_message or not user_message.reply_to_message.photo:
        await user_message.reply_text("Bạn cần reply (trả lời) vào một ảnh để dùng làm ảnh chân dung.")
        return

    if not context.args:
        await user_message.reply_text(
            "Bạn chưa cung cấp thông tin. Vui lòng sử dụng định dạng:\n"
            "<code>/cccd Họ và Tên | Ngày sinh | Giới tính | Quốc tịch | Quê quán | Nơi thường trú | Số CCCD | Ngày hết hạn</code>",
            parse_mode='HTML'
        )
        return

    input_text = " ".join(context.args)
    parts = [p.strip() for p in input_text.split('|')]

    if len(parts) != 8:
        await user_message.reply_text(
            f"Thông tin không đủ hoặc sai định dạng ({len(parts)}/8 trường). "
            "Vui lòng cung cấp đủ 8 trường theo định dạng:\n"
            "<code>Họ và Tên | Ngày sinh | Giới tính | Quốc tịch | Quê quán | Nơi thường trú | Số CCCD | Ngày hết hạn</code>",
            parse_mode='HTML'
        )
        return

    data = {
        'hovaten': parts[0],
        'ngaysinh': parts[1],
        'gioitinh': parts[2],
        'quoctich': parts[3],
        'quequan': parts[4],
        'thuongtru': parts[5],
        'socccd': parts[6],
        'ngayhethan': parts[7],
    }

    if not is_valid_date(data['ngaysinh']):
        await user_message.reply_text("Ngày sinh không hợp lệ. Vui lòng nhập theo định dạng DD/MM/YYYY.")
        return
    if not is_valid_date(data['ngayhethan']):
        await user_message.reply_text("Ngày hết hạn không hợp lệ. Vui lòng nhập theo định dạng DD/MM/YYYY.")
        return

    processing_message = await user_message.reply_text("Đang xử lý ảnh, vui lòng chờ trong giây lát...")
    
    photo_file_id = user_message.reply_to_message.photo[-1].file_id
    new_file = await context.bot.get_file(photo_file_id)
    temp_avatar_path = os.path.join(OUTPUT_DIR, f"avatar_{uuid.uuid4().hex}.jpg")
    try:
        await new_file.download_to_drive(custom_path=temp_avatar_path)
        data['avatar'] = temp_avatar_path
    except Exception as e:
        logger.error(f"Lỗi khi tải ảnh chân dung từ Telegram: {e}", exc_info=True)
        await user_message.reply_text("❌ Lỗi khi tải ảnh chân dung từ Telegram. Vui lòng thử lại.")
        data['avatar'] = ''

    generated_image_buffer = create_cccd_front(data)

    if generated_image_buffer:
        try:
            await user_message.reply_photo(photo=InputFile(generated_image_buffer, filename="cccd_front.png"))
        except Exception as e:
            logger.error(f"Lỗi khi gửi ảnh CCCD về Telegram: {e}", exc_info=True)
            await user_message.reply_text("❌ Lỗi khi gửi ảnh CCCD về Telegram. Vui lòng thử lại.")
    else:
        await user_message.reply_text("❌ Đã xảy ra lỗi khi tạo ảnh CCCD. Vui lòng kiểm tra lại thông tin và các file cấu hình (phôi ảnh, font) trên server.")
    
    if os.path.exists(temp_avatar_path):
        os.remove(temp_avatar_path)
    
    await processing_message.delete()
    if update.message.message_id != processing_message.message_id:
        await update.message.delete()

def main() -> None:
    token = os.getenv("8338495928:AAF9kwzsmBMfqmjOC905mM3ErMbBH-E3SY8")
    if not token:
        logger.error("Môi trường ZPXDEV_SITE_CONGBANGDEVXYZ chưa được đặt. Vui lòng thiết lập biến môi trường này.")
        exit(1)

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cccd", cccd_command))

    logger.info("Bot đang chạy...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
