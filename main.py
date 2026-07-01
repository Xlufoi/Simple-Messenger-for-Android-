import socket
import threading

from kivy.app import App
from kivy.clock import mainthread
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView

PORT = 65432


class RoleScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        layout.add_widget(Label(text='Выберите роль', font_size=24))

        btn_host = Button(text='Быть хостом (сервер)', size_hint_y=None, height=80)
        btn_host.bind(on_release=self.go_host)
        layout.add_widget(btn_host)

        btn_client = Button(text='Подключиться к хосту (клиент)', size_hint_y=None, height=80)
        btn_client.bind(on_release=self.go_client)
        layout.add_widget(btn_client)

        self.add_widget(layout)

    def go_host(self, *_):
        self.manager.current = 'host_setup'

    def go_client(self, *_):
        self.manager.current = 'client_setup'


class HostSetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        self.status = Label(
            text=f'Порт: {PORT}\nНажмите "Старт", чтобы начать ожидание подключения.'
        )
        layout.add_widget(self.status)

        start_btn = Button(text='Старт', size_hint_y=None, height=80)
        start_btn.bind(on_release=self.start_server)
        layout.add_widget(start_btn)

        back_btn = Button(text='Назад', size_hint_y=None, height=60)
        back_btn.bind(on_release=lambda *_: setattr(self.manager, 'current', 'role'))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def start_server(self, *_):
        self.status.text = 'Ожидание подключения...'
        threading.Thread(target=self._server_thread, daemon=True).start()

    def _server_thread(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', PORT))
            s.listen(1)
            conn, addr = s.accept()
        except Exception as e:
            self._set_error(f'Ошибка сервера: {e}')
            return
        self._connected(conn, addr)

    @mainthread
    def _set_error(self, text):
        self.status.text = text

    @mainthread
    def _connected(self, conn, addr):
        chat_screen = self.manager.get_screen('chat')
        chat_screen.set_connection(conn, f'{addr[0]}:{addr[1]}')
        self.manager.current = 'chat'


class ClientSetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=20)
        layout.add_widget(Label(text='Введите публичный IP-адрес сервера:'))

        self.ip_input = TextInput(multiline=False, size_hint_y=None, height=60)
        layout.add_widget(self.ip_input)

        self.status = Label(text='')
        layout.add_widget(self.status)

        connect_btn = Button(text='Подключиться', size_hint_y=None, height=80)
        connect_btn.bind(on_release=self.connect)
        layout.add_widget(connect_btn)

        back_btn = Button(text='Назад', size_hint_y=None, height=60)
        back_btn.bind(on_release=lambda *_: setattr(self.manager, 'current', 'role'))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def connect(self, *_):
        ip = self.ip_input.text.strip()
        if not ip:
            self.status.text = 'Введите IP-адрес.'
            return
        self.status.text = 'Подключение...'
        threading.Thread(target=self._connect_thread, args=(ip,), daemon=True).start()

    def _connect_thread(self, ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((ip, PORT))
            s.settimeout(None)
        except socket.gaierror:
            self._set_error('Ошибка: неверный формат IP-адреса.')
            return
        except ConnectionRefusedError:
            self._set_error('В подключении отказано. Сервер недоступен или закрыт порт.')
            return
        except (socket.timeout, TimeoutError):
            self._set_error('Превышено время ожидания. Проверьте проброс портов на роутере сервера.')
            return
        except Exception as e:
            self._set_error(f'Сбой подключения: {e}')
            return
        self._connected(s, ip)

    @mainthread
    def _set_error(self, text):
        self.status.text = text

    @mainthread
    def _connected(self, conn, ip):
        chat_screen = self.manager.get_screen('chat')
        chat_screen.set_connection(conn, ip)
        self.manager.current = 'chat'


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = None

        root = BoxLayout(orientation='vertical')
        self.title_label = Label(text='Не подключено', size_hint_y=None, height=40)
        root.add_widget(self.title_label)

        self.log_label = Label(
            text='', size_hint_y=None, halign='left', valign='top', markup=True
        )
        self.log_label.bind(texture_size=self._update_log_height)
        self.log_label.text_size = (None, None)

        self.scroll = ScrollView()
        self.scroll.add_widget(self.log_label)
        root.add_widget(self.scroll)

        input_row = BoxLayout(size_hint_y=None, height=60)
        self.msg_input = TextInput(multiline=False)
        self.msg_input.bind(on_text_validate=self.send_message)
        send_btn = Button(text='Отправить', size_hint_x=None, width=150)
        send_btn.bind(on_release=self.send_message)
        input_row.add_widget(self.msg_input)
        input_row.add_widget(send_btn)
        root.add_widget(input_row)

        disconnect_btn = Button(text='Отключиться', size_hint_y=None, height=50)
        disconnect_btn.bind(on_release=self.disconnect)
        root.add_widget(disconnect_btn)

        self.add_widget(root)

    def on_size(self, *_):
        self.log_label.text_size = (self.scroll.width, None)

    def _update_log_height(self, *_):
        self.log_label.height = self.log_label.texture_size[1]
        self.log_label.text_size = (self.scroll.width, None)

    def set_connection(self, conn, peer_label):
        self.conn = conn
        self.title_label.text = f'Подключено: {peer_label}'
        self.log_label.text = ''
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _receive_loop(self):
        while True:
            try:
                data = self.conn.recv(1024)
                if not data:
                    break
                self._append_log(f'[Собеседник]: {data.decode("utf-8", errors="replace")}')
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break
        self._append_log('[Система]: Соединение разорвано.')

    @mainthread
    def _append_log(self, line):
        self.log_label.text += ('\n' if self.log_label.text else '') + line
        self.scroll.scroll_y = 0

    def send_message(self, *_):
        msg = self.msg_input.text.strip()
        if not msg or not self.conn:
            return
        try:
            self.conn.sendall(msg.encode('utf-8'))
            self._append_log(f'[Вы]: {msg}')
            self.msg_input.text = ''
        except (ConnectionResetError, BrokenPipeError, OSError):
            self._append_log('[Система]: Ошибка отправки, соединение потеряно.')

    def disconnect(self, *_):
        if self.conn:
            try:
                self.conn.close()
            except OSError:
                pass
            self.conn = None
        self.manager.current = 'role'


class ChatApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(RoleScreen(name='role'))
        sm.add_widget(HostSetupScreen(name='host_setup'))
        sm.add_widget(ClientSetupScreen(name='client_setup'))
        sm.add_widget(ChatScreen(name='chat'))
        return sm


if __name__ == '__main__':
    ChatApp().run()
