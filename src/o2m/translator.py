import re
import argparse
import sys
import os
import json
import glob
import mimetypes
import datetime
import subprocess
import shutil
import requests
import markdown
import requests

# End point for yout requests
    
def postToMedium(token, title, tags, content):
    url = "https://api.medium.com/v1"

    # header requred
    header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": "api.medium.com",
        "TE": "Trailers",
        "Authorization": f"Bearer {token}",
        "Upgrade-Insecure-Requests": "1",
    }
    
    data = {
        "title": f"{title}",
        "contentFormat": "markdown",
        "content": f"{content}",
        "tags": tags,
        "publishStatus": "public",  # "public" will publish to gibubfor putting draft use value "draft"
    }
    response = requests.get(
        url=url + "/me",  # https://api.medium.com/me
        headers=header,
        params={"accessToken": token},
    )
    # checking response from server
    if response.status_code == 200:
        response_json = response.json()
        userId = response_json["data"]["id"]
        print(userId)
        response = requests.post(
            url=f"{url}/users/{userId}/posts",  # https://api.medium.com/me/users/{userId}/posts
            headers=header,
            data=data,
        )
        print(response.text)
        if response.status_code == 200:
            response_json = response.json()
            url = response_json["data"]["url"]
            print(url)  # this url where you can acess your url


def postImage(token, image_path):
    image_type = mimetypes.guess_type(image_path)[0]
    url = "https://api.medium.com/v1"

    # header requred
    header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Host": "api.medium.com",
        "TE": "Trailers",
        "Authorization": f"Bearer {token}",
        "Upgrade-Insecure-Requests": "1",
    }
    
    with open(image_path, "rb") as image:
        files = {"image": (image_path, image, image_type)}
        response = requests.request(
            "post",
            url=url + "/images",  # https://api.medium.com/images
            headers=header,
            files=files
        )
        # checking response from server
        if 200 <= response.status_code < 300:
            response_json = response.json()
            return response_json["data"]["url"]
        else:
            return None

# Read config filepython -m build
## Input:
## - config file path
## Output:
## - list of obsidian home paths
def getConfigurations(config_file_path=""):
    if len(config_file_path) == 0:
        # TODO: add Windows config file path
        config_file_path = os.path.expanduser("~") + "/.config/o2m/config.json"

    if os.path.isfile(config_file_path):
        # open JSON file
        config_file = open(config_file_path, "r")
        # read date from file
        data = json.loads(config_file.read())
        return data
    else:
        print("Config file not found")
        exit(0)


class translator_tp:
    def __init__(self):
        self.config = None
        self.input = None
        self.tags = []
        self.links = []
        self.date = []
        self.time = None
        self.title = ""

    def get_file_type(self, file_name: str):
        mimestart = mimetypes.guess_type(file_name)[0].lower()
        mime_parse = mimestart.split("/")
        if mime_parse[0] == "image":
            return "image"
        if mime_parse[1] == "pdf":
            return "pdf"
        return "undefined"

    def get_file_type_detail(self, file_name: str):
        mimestart = mimetypes.guess_type(file_name)[0].lower()
        mime_parse = mimestart.split("/")
        return mime_parse[1]

    def read_and_find_info(self):
        tag_pattern = r"#[^\ ^#^\s]+"
        link_pattern = r"\!\[\[.+\]\]"

        # Find all links and tags in an obsidian file
        with open(self.input, "r") as file:
            for line in file:
                tag_list = re.findall(tag_pattern, line)
                link_list = re.findall(link_pattern, line)
                if len(tag_list) > 0:
                    if len(self.tags) == 0:
                        self.tags = tag_list
                if len(link_list) > 0:
                    self.links += link_list
            file.close()
        # Remove first '#' from the beginning of the line
        for index in range(len(self.tags)):
            self.tags[index] = self.tags[index][1:].split("/")[-1]
        self.tags = list(set(self.tags))

        # Update time as last modified time
        file_modify_date = (
            str(datetime.datetime.fromtimestamp(os.path.getmtime(self.input)))
            .split(" ")[0]
            .split("-")
        )
        self.time = str(
            datetime.datetime.fromtimestamp(os.path.getmtime(self.input))
        ).split(".")[0]
        self.date = [int(item) for item in file_modify_date]

        # Get filename as title
        self.title = self.input.split("/")[-1].split(".")[0]

    def get_file_location(self, name):
        """
        finds the location of a file in obsidian
        Args:
         - self, name

        Return:
         - file_paths[0]
        """
        name = name[3:-2].replace(" ", " ")
        target_base = self.config["obsidian_target"]
        file_paths = []
        # searches for findpath in the target base directory
        for findpath in target_base:
            bashCommand = ["find", findpath, "-name", f"*{name}*"]
            # print(bashCommand)
            process = subprocess.Popen(bashCommand, stdout=subprocess.PIPE)
            output, error = process.communicate()
            file_paths = list(output.decode("utf-8").split("\n"))
            # print(output)
            if len(file_paths) > 0:
                break
        if len(file_paths) == 0:
            print("Cannot find file in path")
            exit(0)
        return file_paths[0]

    def translate(self):
        tag_pattern = r"#[^\ ^#^\s]+"
        link_pattern = r"\!\[\[.+\]\]"
        
        token = self.config["medium_token"]        
        # os.mkdir(output_dir_name)

        image_counter = 0

        md_file_content = ""
        info_header = "# " + self.title + "\n"
        # output_file.write(info_header)
        md_file_content += info_header

        more_tag = False
        with open(self.input) as input_file:
            for line in input_file:
                if re.match(tag_pattern, line):
                    # tag is handled before
                    continue
                if re.match(link_pattern, line):
                    # add a new link here
                    link_file_name = re.findall(link_pattern, line)[0]
                    link_file_location = self.get_file_location(link_file_name)
                    link_file_location = link_file_location.replace(" ", " ")
                    link_file_type = self.get_file_type(link_file_location)
                    if link_file_type == "undefined" or link_file_type == "pdf":
                        # do not care about undefined files
                        continue
                    elif link_file_type == "image":
                        image_counter += 1
                        # print out image link here
                        img_url = postImage(token, link_file_location)
                        # img_url = "https://cdn-images-1.medium.com/proxy/1*kmMg2ATucBajGxo9EBi30Q.png"
                        md_file_content += (
                            f"![image_{image_counter}]({img_url})" + "\n"
                        )
                else:
                    # Common Line
                    md_file_content += line
            if len(self.tags) == 0:
                self.tags.append("development")
                self.tags.append("blog")
            if len(self.links) == 1:
                self.tags.append("blog")
            postToMedium(token, self.title, self.tags, md_file_content)


def o2m():
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="get the obs markdown filename", type=str)
    
    args = parser.parse_args()
    if str(args.filename)[-3:] != ".md":
        print("This is not a .md file")
        return 0

    vm = translator_tp()
    vm.input = args.filename
    vm.name = vm.input.split("/")[-1][0:-3]
    vm.config = getConfigurations()

    vm.read_and_find_info()
    vm.translate()
    return 1


if __name__ == "__main__":
    o2m()
