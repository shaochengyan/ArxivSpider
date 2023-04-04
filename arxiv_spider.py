import urllib
from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import date
import yaml


def create_dir(dir):
    if not os.path.isdir(dir):
        os.makedirs(dir)

def get_config(yaml_file):
    """ brief
    读取文件并将解析好的内容返回
    """
    fin = open(yaml_file, "r")
    config = yaml.safe_load(fin)
    fin.close()

    # create dir
    create_dir(config["arxiv_data_dir"])
    create_dir(config["map_data_dir"])
    return config


url_arxiv_base = "https://arxiv.org"
config = get_config("./config.yaml")


def get_url_bs(url):
    html = urlopen(url)
    bs = BeautifulSoup(html, "html.parser")
    return bs


def url_all_papers_this_week(domain="cs.CV"):
    """
    从主页中获取给定领域的all页面的url
    """
    url_recent = "https://arxiv.org/list" + "/{}/recent".format(domain)
    html = urlopen(url_recent)
    bs = BeautifulSoup(html, "html.parser")
    href = bs.find("a", text="all").attrs["href"]
    return url_arxiv_base + href


def get_today_all_paper_id(url_all):
    """
    从 all url 中获取当天所有paper的id
    """
    bs_all = get_url_bs(url_all)
    # 第一个datalist的所有data 即当天的所有paper
    papers_all = bs_all.find("dl").find_all("dt")  
    id_list = []
    for paper in papers_all:
        # paper id:2303.17606
        paper_id = paper.find("a", {"title": "Abstract"}).text[6:]
        id_list.append(paper_id)
    return id_list



def search_kw_in_text(text, kw_list_dict):
    """
    检测 text 中是否包含 关键词组合
    """
    domain_list = []
    domain_mini = ""  # 多个领域
    for domain, kw_list in kw_list_dict.items():
        matched_kw = []
        for kw in kw_list:
            if len(kw) == 1:
                pattern = re.compile(kw[0], re.IGNORECASE)
            else:
                pattern = re.compile("&".join(kw), re.IGNORECASE)
            
            match = pattern.search(text)
            if match:
                matched_kw.extend(kw)
        if len(matched_kw) > 0:
            domain_list.extend(matched_kw)
            domain_mini = domain

    if len(domain_list) > 0:
        return domain_mini, list(set(domain_list))
    else:
        return None


def get_paper_info_dict(id):
    info_dict = {
        "url_main_page": "https://arxiv.org/abs/{}".format(id), 
        "url_pdf": "https://arxiv.org/pdf/{}.pdf".format(id)
    }

    bs_main_page = get_url_bs(info_dict["url_main_page"])
    
    # title
    title = bs_main_page.find("h1", {"class": "title mathjax"}).text[6:]
    info_dict["title"] = title

    # absatract and code
    abstract = bs_main_page.find("blockquote").text.strip()[11:]
    abstract = abstract.replace("\n", " ")
    code_url = bs_main_page.find("blockquote").find("a", href=re.compile("(.+)github(.+)"))
    if code_url:
        code_url = code_url.attrs["href"]
    info_dict["abstract"] = abstract
    info_dict["code_url"] = code_url
    return info_dict


class JsonDumpReader:
    def __init__(self, filename=None) -> None:
        if filename is None:
            filename = "test.json"
        self.is_exist = os.path.isfile(filename)
        self.filename = filename
    
    def save(self, info_dict_list):
        if self.is_exist:
            print("\"{}\" exsits! Please delete it before run.".format(self.filename))
            return
        with open(self.filename, "w") as fp:
            data_str = json.dumps(info_dict_list)
            fp.write(data_str)

    def read(self):
        if not self.is_exist:
            print("\"{}\" not exsits! Please first save it. ".format(self.filename))
        with open(self.filename, "r") as fp:
            return json.loads(fp.read())

class ArxivSpider:
    def __init__(self, domain="cs.CV"):
        self.domain = domain
        self.save_filename = os.path.join(config["arxiv_data_dir"], "arxiv-{}.json".format(date.today()))

    def run(self, start=0):
        if os.path.exists(self.save_filename):
            print("Json exists!")
            return
        url_all = url_all_papers_this_week()
        ids = get_today_all_paper_id(url_all)
#        print(ids)
#        return
        saver = JsonDumpReader(self.save_filename)
        total_num = len(ids)
        info_dict_list = []
        for i, id in enumerate(ids):
            info_dict = get_paper_info_dict(id)
            print("{}/{}".format(i+1, total_num), id, " ", info_dict["title"])
            info_dict_list.append(info_dict)
            
            # if i > 5:
            #     break

        saver.save(info_dict_list)


class MarkdownWriter:
    def __init__(self, filename) -> None:
        self.filename = filename
    
    def save_info_dict_dict(self, info_dict_dict):
        with open(self.filename, mode="w") as fp:
            for domain in info_dict_dict:  # each domain
                info_dict_list = info_dict_dict[domain]
                if len(info_dict_list) == 0:
                    continue

                fp.write("\n# {}\n".format(domain))

                for info_dict in info_dict_list:  # each info_dict
                    self.save_info_dict(fp, info_dict)
        

    def save_info_dict(self, fp, info_dict):
        fp.write("## {}\n".format(info_dict["title"]))

        # Keywords
        Keywords = info_dict["Keywords"]
        fp.write("> - **KEYWORDS: {}**\n".format(Keywords))
        
        # url
        fp.write("> - [{}]({})\n".format("PDF", info_dict["url_pdf"]))
        fp.write("> - [{}]({})\n".format("Main Page", info_dict["url_main_page"]))
        if info_dict["code_url"]:
            fp.write("> - [{}]({})\n".format("CODE", info_dict["code_url"]))

        # 加粗 keywords
        Keywords_list = Keywords.split(" ")
        # print(Keywords_list)
        abstract = info_dict["abstract"]
        for item in Keywords_list:
            pattern = re.compile("{}".format(item), re.IGNORECASE)
            abstract = pattern.sub("**{}**".format(item), abstract)
        fp.write("\n**Abstract: ** {}\n".format(abstract))


def spider_today():
    spider = ArxivSpider("cs.CV")
    spider.run()


def filter_and_kws_paper(md_name, keywords_dict):
    # 读取json信息并解析 -> 筛选关键词 -> 输出方便处理的形式
    filename = os.path.join(config["arxiv_data_dir"], "arxiv-{}.json".format(date.today()))
    reader = JsonDumpReader(filename)
    data = reader.read()

    # 筛选info dict
    papers_dict = dict()
    for key in keywords_dict.keys():
        papers_dict[key] = []
    for info_dict in data:
        rslt = search_kw_in_text(info_dict["abstract"], keywords_dict)
        if rslt is None:
            continue
        domain, kw = rslt
        info_dict["Keywords"] = " ".join(kw)
        # print(kw)
        papers_dict[domain].append(info_dict)

    # print(papers_dict)
    
    # save to markdown by different domain
    mdfilename = os.path.join(config["map_data_dir"], "arxiv-map-{}-{}.md".format(date.today(), md_name))
    mder = MarkdownWriter(mdfilename)
    mder.save_info_dict_dict(papers_dict)


if __name__=="__main__":
    # 爬取当日所有文章信息 -> 并存储为json文件
    spider_today()

    # 筛选文件 via kw_list
    domain_kw_dict = config["kw_list"]
    for domain_name, domain_kw in domain_kw_dict.items():
        print(domain_name, domain_kw)
        filter_and_kws_paper(domain_name, domain_kw)
