import re
from collections import UserDict
from datetime import datetime, timedelta
from difflib import get_close_matches
from pathlib import Path
from typing import Dict, List
import os
import shutil
from pick import pick
from models import Records, Addresses, Emails, Notes, Phones, Tags
from mongoengine import connect, DoesNotExist

con = connect(db='mongo_test', host='localhost', port=27017)

CATEGORIES = {'images': ('JPEG', 'PNG', 'JPG', 'SVG'), 'documents': ('DOC', 'DOCX', 'TXT', 'PDF', 'XLSX', 'PPTX'),
              'audio': ('MP3', 'OGG', 'WAV', 'AMR'), 'video': ('AVI', 'MP4', 'MOV', 'MKV'), 'archives': ('ZIP', 'GZ', 'TAR')}

file_log = []

def folder_path(path):
    if os.path.exists(path):
        global base_path
        base_path = path
        return sort_files(base_path)
    else:
        print('Wrong path!')

def rename_exists_files(name):
    return name + '_edit_' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')

def log():
    final_dict = {}
    for i in file_log:
        for k, v in i.items():
            final_dict.setdefault(k, []).append(v)
    for k, v in final_dict.items():
        print(f'---{k}---')
        print(', '.join(v))
    print(f"Sorting in the {base_path} catalog has been completed successfully.")

def ignore_list():
    ignore = []
    for k in CATEGORIES.keys():
        ignore.append(k)
    return ignore

def remove_folders(path):
    folders = list(os.walk(path))
    for path, _, _ in folders[::-1]:
        if len(os.listdir(path)) == 0:
            os.rmdir(path)

def move_files(file_path):
    dirname, fname = os.path.split(file_path)
    extension = os.path.splitext(fname)[1].upper().replace('.', '')
    for k, v in CATEGORIES.items():
        if extension in v:
            os.makedirs(base_path + '/' + k, exist_ok=True)
            if os.path.exists(os.path.join(base_path + '/' + k, fname)):
                new_f_renamed = rename_exists_files(os.path.splitext(fname)[0]) + os.path.splitext(fname)[1]
                shutil.move(os.path.join(file_path), os.path.join(base_path + '/' + k, new_f_renamed))
                file_log.append({k: new_f_renamed})
            else:
                shutil.move(os.path.join(file_path), os.path.join(base_path + '/' + k, fname))
                file_log.append({k: fname})

def sort_files(path):
    subfolders = []
    files = []
    ignore = ignore_list()
    for i in os.scandir(path):
        if i.is_dir():
            if i.name not in ignore:
                old_path = os.path.dirname(i.path)
                os.rename(os.path.join(old_path, i.name), os.path.join(old_path, i.name))
                subfolders.append(os.path.join(old_path, i.name))
        if i.is_file():
            old_path = os.path.dirname(i.path)
            os.rename(os.path.join(old_path, i.name), os.path.join(old_path, i.name))
            files.append(os.path.join(old_path, i.name))
            move_files(os.path.join(old_path, i.name))
    for dir in list(subfolders):
        sf, i = sort_files(dir)
        subfolders.extend(sf)
        files.extend(i)

    return subfolders, files

def sort_files_entry_point(path):
    folder_path(path)
    remove_folders(base_path)
    log()


class InvalidPhoneNumber(Exception):
    """Exception in case of incorrect phone number input"""


class InvalidEmailAddress(Exception):
    """Exception in case of incorrect E-mail input"""


class InvalidBirthday(Exception):
    """Exception in case of incorrect Birthday input"""


class AddressBook(UserDict):
    def __get_params(self, params: Dict[str, str], msg: str = None) -> List[str]:
        msg = "Please enter the " if not msg else msg
        params_keys = list(params.keys())
        for index in range(len(params)):
            obj_name = params_keys[index]
            """If one of the parameters specified in the array is requested, 
            the input string must be split by the ";" and convert to array."""
            if obj_name in ["phones", "addresses", "emails", "notes", "tags"]:
                params[obj_name] = input(f"{msg}{obj_name}. Separator symbol for {obj_name} is \";\": ")
            else:
                params[obj_name] = input(f"{msg}{obj_name}: ")
        return params.values()

    def phone_valid(self, value):
        if len(value) == 13:
            self._value = value
            return value
        else:
            raise InvalidPhoneNumber

    def email_valid(self, value):
        if self.__check_email(value):
            self._value = value
            return value
        else:
            raise InvalidEmailAddress

    def birthday_valid(self, value):
        try:
            self._value = datetime.strptime(value, "%d.%m.%Y").strftime("%d.%m.%Y")
            return value
        except ValueError:
            raise InvalidBirthday

    def __check_email(self, email: str) -> bool:
        matched = re.match(r"[a-z][a-z|\d._]{1,}@[a-z]{1,}\.\w{2,}", email, re.IGNORECASE)
        return bool(matched)

    def add_record(self) -> None:
        new_record = self.__get_params({"name": "", "phones": "", "birthday": "", "addresses": "", "emails": "", "notes": ""})
        new_record = [i for i in new_record]
        try:
            record = Records.objects(name=new_record[0].capitalize())
            if not record:
                rec = Records(name=new_record[0].capitalize(), birthday=self.birthday_valid(new_record[2]))
                email = Emails(title=self.email_valid(new_record[4]), records=rec)
                addresses = Addresses(title=new_record[3], records=rec)
                phones = Phones(number=self.phone_valid(new_record[1]), records=rec)
                notes = Notes(title=new_record[5], records=rec)
                rec.save(), email.save(), addresses.save(), phones.save(), notes.save()
            else:
                print(f'The username {new_record[0].capitalize()} is already registered in the address book. Choose something else.')
        except InvalidPhoneNumber:
            print(f"The phone number {new_record[1]} is invalid")
        except InvalidEmailAddress:
            print(f"The email {new_record[4]} is invalid")
        except InvalidBirthday:
            print(f"The birthday {new_record[2]} is invalid")

    def _edit_name(self, contact) -> None:
        qs = Records.objects.get(id=contact)
        print(f"The following user names are registered in the address book: {qs.name}")
        new_name = ''.join(self.__get_params({"new name of user": ""})).strip().capitalize()
        if new_name:
            new_qs = Records.objects(name=new_name)
            if not new_qs:
                qs.update(name=new_name)
            else:
                print(f"The username {new_name} is already registered in the address book. Choose something else.")
        else:
            print("You have not provided a new username.")

    def _edit_phone(self, contact) -> None:
        qs = Phones.objects(records=contact)
        option = pick([i.number for i in qs], "Select the phone number you want to edit.", indicator="=>")
        option = option[0]
        option = re.sub(r'[^0-9.]+', r'', str(option))
        print(f"You have selected: {option}")
        new_number = ''.join(self.__get_params({"new phone number": ""})).strip()
        try:
            self.phone_valid(new_number)
            Phones.objects(number=option, records=contact).update(number=new_number)
        except InvalidPhoneNumber:
            print("You entered an invalid phone number.This data is not recorded.")

    def _edit_birthday(self, contact) -> None:
        qs = Records.objects.get(id=contact)
        print(f"Current birthday of user {qs.birthday}")
        new_birthday = ''.join(self.__get_params({"birthday of user": ""})).strip()
        try:
            self.birthday_valid(new_birthday)
            qs.update(birthday=new_birthday)
        except InvalidBirthday:
            print("You entered an invalid birthday.This data is not recorded.")

    def _edit_address(self, contact) -> None:
        qs = Addresses.objects(records=contact)
        option = pick([i.title for i in qs], "Select the address you want to edit.", indicator="=>")
        option = option[0]
        option = re.sub(r'[^A-Za-z0-9.]+', r'', str(option))
        print(f"You have selected: {option}")
        new_address = ''.join(self.__get_params({"new address": ""})).strip()
        if new_address:
            Addresses.objects(title=option, records=contact).update(title=new_address)

    def _edit_email(self, contact) -> None:
        qs = Emails.objects(records=contact)
        option = pick([i.title for i in qs], "Select the email you want to edit.", indicator="=>")
        option = option[0]
        option = re.sub(r'[^A-Za-z0-9-@.]+', r'', str(option))
        print(f"You have selected: {option}")
        new_email = ''.join(self.__get_params({"new email": ""})).strip()
        if new_email:
            try:
                self.email_valid(new_email)
                Emails.objects(title=option, records=contact).update(title=new_email)
            except InvalidEmailAddress:
                print("You entered an invalid email address.This data is not recorded.")
        else:
            print("You have not provided a new email.")

    def _edit_note(self, contact) -> None:
        qs = Notes.objects(records=contact)
        option = pick([i.title for i in qs], "Select the note you want to edit.", indicator="=>")
        option = option[0]
        option = re.sub(r'[^A-Za-z0-9.]+', r'', str(option))
        print(f"You have selected: {option}")
        new_note = ''.join(self.__get_params({"new note": ""})).strip()
        if new_note:
            try:
                Notes.objects(title=option, records=contact).update(title=new_note)
            except InvalidEmailAddress:
                print("You entered an invalid note address.This data is not recorded.")
        else:
            print("You have not provided a new note.")

    def _edit_tag(self, contact) -> None:
        try:
            qs = Notes.objects.get(records=contact)
            option = pick([i.title for i in qs['tags']], "Select the tag for which you want to edit.", indicator="=>")
            option = option[0]
            option = re.sub(r'[^A-Za-z0-9.]+', r'', str(option))
            print(f"You have selected: {option}")
            new_tag = ''.join(self.__get_params({"new tag": ""})).strip()
            if new_tag:
                Notes.objects(records=contact, tags__title=option).update(tags=[Tags(title=new_tag)])
        except DoesNotExist:
            print('No tags found!')

    def edit_record(self) -> None:
        qs = Records.objects()
        option = pick([i.name for i in qs], \
            "Select the name of the user whose data you want to edit.", indicator="=>")[0]
        contact = Records.objects.get(name=option)
        if contact:
            function_names = [self._edit_name, self._edit_phone, self._edit_birthday, \
                self._edit_address, self._edit_email, self._edit_note, self._edit_tag]
            description_function = ["Edit user name", "Edit phone", \
                "Edit birthday", "Edit addresses", "Edit emails", \
                "Edit notes", "Edit tags", "FINISH EDITING"]
            base_msg = f"Select what information for the user {contact['name']} you would like to change.\n{'='*60}"
            option, index = pick(description_function, base_msg, indicator="=>")
            while index != len(description_function)-1:
                print(f"You have selected an {option} option.\nLet's continue.\n{'='*60}")
                function_names[index](contact['id'])
                option, index = pick(description_function, base_msg, indicator="=>")

    def add_tags(self) -> None:
        contact = ''.join(self.__get_params({"name of contact": ""})).capitalize()
        try:
            record = Records.objects.get(name=contact)
            qs = Notes.objects(records=record)
            option = pick([i.title for i in qs], "Select the note where you want to add tags:", indicator="=>")
            option = option[0]
            base_msg = f"Specify tags that you want to add to the selected note by {option}. "
            new_tag = ''.join(self.__get_params({f"{base_msg}": ""})).strip()
            if new_tag:
                Notes.objects.get(title=option, records=record).update(tags=[Tags(title=new_tag)])
        except DoesNotExist:
            print(f"The user {contact} was not found in the address book.")

    def del_contact(self) -> None:
        contact = ''.join(self.__get_params({"contact": ""})).capitalize()
        try:
            Records.objects.get(name=contact).delete()
            print(f"Contact {contact} was removed!")
        except DoesNotExist:
            print(f"Contact {contact} not found!")

    def holidays_period(self) -> None:
        qs = Records.objects()
        result = []
        try:
            period = int(''.join(self.__get_params({"period": ""})))
        except ValueError:
            print('Only number allowed!')
        else:
            if period > 365:
                period = 365
            day_today = datetime.now()
            day_today_year = day_today.year
            end_period = day_today + timedelta(days=period+1)
            print(f"Found birthdays for {period} days period: ")
            for i in qs:
                date = datetime.strptime(i.birthday, '%d.%m.%Y').replace(year=end_period.year)
                if day_today_year < end_period.year:
                    if day_today <= date.replace(year=day_today_year) or date <= end_period:
                        result.append(f"{i.name}")
                else:
                    if day_today <= date.replace(year=day_today_year) <= end_period:
                        result.append(f"{i.name}")
            if not result:
                result.append(f"No contacts with birthdays for this period.")
            print('\n'.join(result))

    def find_contact(self) -> None:
        contact = ''.join(self.__get_params({"search info": ""})).capitalize()
        try:
            record = Records.objects.get(name=contact)
            qs_phones = Phones.objects(records=record)
            qs_emails = Emails.objects(records=record)
            qs_addres = Addresses.objects(records=record)
            result = [f"Search results for string \"name: {record.name} birthday: {record.birthday} "
                      f"phones: {[i.number for i in qs_phones]} " f"emails: {[i.title for i in qs_emails]} "
                      f"addreses: {[i.title for i in qs_addres]}\": "]
            print('\n'.join(result))
        except DoesNotExist:
            print(f"There is no contact with name: {contact}.")

    def sort_files(self) -> str:
        return sort_files_entry_point((''.join(self.__get_params({"path": ""}))))

    def _find_contact(self, message: str):
        contact = ''.join(self.__get_params({message: ""})).capitalize()
        try:
            qs = Records.objects.get(name=contact)
            return qs.id
        except DoesNotExist:
            print("There is no contact with provided name.")

    def add_note(self) -> None:
        record = self._find_contact("contact to add a note")
        if record:
            note = ''.join(self.__get_params({"new note": ""})).strip()
            Notes(title=note, records=record).save()
            print("Note was added.")

    def print_notes(self) -> None:
        record = self._find_contact("contact to display")
        if record:
            qs = Notes.objects.get(records=record)
            for i in qs:
                print(i.title)

    def del_note(self) -> None:
        record = self._find_contact("contact")
        qs = Notes.objects(records=record)
        if qs:
            option = pick([i.title for i in qs], "Select the note you want to delete:", indicator="=>")[0]
            Notes.objects.get(records=record, title=option).delete()
            print("Note was deleted.")

    def find_sort_note(self) -> None:
        tag_name = "".join(self.__get_params({"tag name": ""}))
        qs = Notes.objects(tags__title=tag_name)
        for i in qs:
            print(i.title)

    def show_contacts(self):
        qs = Records.objects()
        for i in qs:
            print(i.name, i.birthday)

    def show_commands(self) -> None:
        """Displaying commands with the ability to execute them"""

        option, index = pick(commands_desc, \
            f"Command name and description. Select command.\n{'='*60}", indicator="=>")
        print(f"You have chosen a command: {option}.\nLet's continue.\n{'='*60}")
        functions_list[index]()


class CommandHandler:

    def __call__(self, command: str) -> bool:
        if command in exit_commands:
            return False
        elif command in action_commands:
            commands_func[command]()
            return True
        command = get_close_matches(command, action_commands + exit_commands)
        in_exit = not set(command).isdisjoint(exit_commands)
        if in_exit:
            return False
        in_action = not set(command).isdisjoint(action_commands)
        if in_action:
            if len(command) == 1:
                commands_func[command[0]]()
            elif len(command) > 1:
                command = pick(command, TITLE, indicator="=>")[0]
                print(f"You have selected the {command} command. Let's continue.")
                commands_func[command]()
        else:
            print("Sorry, I could not recognize this command!")
        return True


book = AddressBook()
TITLE = "We have chosen several options from the command you provided.\nPlease choose the one that you need."
action_commands = ["help", "add_contact", "edit_record", "holidays_period", "print_notes", "add_note", \
    "del_note", "find_note", "add_tag", "sort_files", "find_contact", "del_contact", "show_contacts"]
description_commands = ["Display all commands", "Add user to the address book", \
    "Edit information for the specified user", "Amount of days where we are looking for birthdays", \
    "Show notes for the specified user", "Add notes to the specified user", \
    "Delete the notes for the specified user", "Find notes for specified user", \
    "Add tag for the specified user", "Sorts files in the specified directory", \
    "Search for the specified user by name", "Delete the specified user", \
    "Show all contacts in address book", "Exit from program"]
exit_commands = ["good_bye", "close", "exit"]
functions_list = [book.show_commands, book.add_record, book.edit_record, book.holidays_period, \
    book.print_notes, book.add_note, book.del_note, book.find_sort_note, book.add_tags, \
    book.sort_files, book.find_contact, book.del_contact, book.show_contacts, exit]
commands_func = {cmd: func for cmd, func in zip(action_commands, functions_list)}
commands_desc = [f"{cmd:<15} -  {desc}" for cmd, desc in zip(action_commands + [', '.join(exit_commands)], description_commands)]

if __name__ == "__main__":
    current_script_path = Path(__file__).absolute()
    file_bin_name = f"{current_script_path.stem}.bin"
    data_file = current_script_path.parent.joinpath(file_bin_name)
    """get data file from current directory"""
    cmd = CommandHandler()
    input_msg = input("Hello, please enter the command: ").lower().strip()
    while cmd(input_msg):
        input_msg = input("Please enter the command: ").lower().strip()
    print("Have a nice day... Good bye!")
