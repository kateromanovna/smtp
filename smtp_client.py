import base64
import socket
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os


def request(socket, request: str, expected_code: int) -> str:
    socket.send((request + '\n').encode())
    recv_data = socket.recv(65535).decode()
    print(recv_data)  # Для отладки
    code = int(recv_data[0:3])
    if code != expected_code:
        raise Exception(f"Expected code {expected_code}, but got {code}")
    return recv_data


def create_mime_message(subject, sender, recipient, body_text, attachment_paths):
    message = MIMEMultipart()
    message['Subject'] = Header(subject, 'utf-8').encode()
    message['From'] = sender
    message['To'] = recipient
    message.attach(MIMEText(body_text, 'plain', 'utf-8'))

    for path in attachment_paths:
        part = MIMEBase('application', "octet-stream")
        with open(path, 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
        message.attach(part)

    return message.as_string()


if __name__ == '__main__':
    recipient, subject, attachments = '', '', []
    with open('configuration/configuration.txt', encoding='utf-8') as file:
        lines = file.readlines()
        host_addr = lines[0][5::].strip()
        port = int(lines[1][5::].strip())
        user_name = lines[2][5::].strip()
        password = lines[3][9::].strip()
        domain = lines[4][7::].strip()
        recipient = lines[5][3::].strip()
        subject = lines[6][8::].strip()
        attachments = [line.strip() for line in lines[7:]]

    body_text = ''
    with open("configuration/email_text.txt", encoding='utf-8') as body_file:
        body_text = body_file.read()

    attachment_paths = [os.path.join(os.getcwd(), attachment) for attachment in attachments]

    mime_message = create_mime_message(subject, user_name + domain, recipient, body_text, attachment_paths)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((host_addr, port))
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        client = context.wrap_socket(client, server_hostname=host_addr)
        recv_data = client.recv(1024).decode()
        print(recv_data)
        request(client, f"EHLO {user_name}", 250)

        base64login = base64.b64encode(user_name.encode()).decode()
        base64password = base64.b64encode(password.encode()).decode()

        request(client, 'AUTH LOGIN', 334)
        request(client, base64login, 334)
        request(client, base64password, 235)

        request(client, f'MAIL FROM:<{user_name + domain}>', 250)
        request(client, f'RCPT TO:<{recipient}>', 250)
        request(client, 'DATA', 354)
        request(client, mime_message + "\r\n.", 250)
