from typing import Tuple
from urllib import request, parse
import json
# local
from .constants import URL, JOB_TAGS


class HeadHunterApiManager:
    @staticmethod
    def prepare_tags(tags: dict) -> str:
        for tag in tags.values():
            # to lower case
            tag = [t.lower() for t in tag]

        # AND & OR - operators from hh.ru api
        type_tag = f"({' OR '.join(tags['type'])})" if ('type' in tags.keys()) and (len(tags['type']) != 0) else ''
        tech_tag = f"({' OR '.join(tags['tech'])})" if ('tech' in tags.keys()) and (len(tags['tech']) != 0) else ''
        city_tag = tags['city']
        # if both are empty, just fill in 'developer', 'cos we don't want to have an empty query
        if type_tag + tech_tag + city_tag == '':
            type_tag = 'developer OR разработчик OR программист'

        return f"{type_tag} AND {tech_tag} AND {city_tag}"

    @staticmethod
    def get_jobs(tags=None, page: int = 1) -> Tuple[list, int]:
        if tags is None:
            tags = {'type': ['developer OR разработчик OR программист'], 'city': ''}
        jobs = []  # jobs to be received
        pages = 1  # pages to be received
        querystring = dict()  # querystring that we will construct

        # prepare tags
        tags_str = HeadHunterApiManager.prepare_tags(tags)

        # update querystring according to hh.ru api specification
        querystring['text'] = tags_str  # set text
        querystring['page'] = page  # set page
        querystring['per_page'] = 10  # 10 jobs per page by default
        querystring['specialization'] = 1  # specialization - "Информационные технологии, интернет, телеком" (id = 1)
        # encode querystring
        querystring = parse.urlencode(querystring)
        # send request to hh.ru api and get data
        with request.urlopen(f'{URL}/vacancies?{querystring}') as response:
            data = response.read()
            data = json.loads(data)
            jobs.extend(data['items'])
            pages = int(data['pages'])
        return jobs, pages

    @staticmethod
    def get_job(link: str) -> dict:
        job_id = link.split('/')[-1]
        job = {}
        with request.urlopen(f'{URL}/vacancies/{job_id}') as response:
            data = response.read()
            job = json.loads(data)
        try:
            job_requirements = job['snippet']['requirement']
        except KeyError:
            job_requirements = ''
        type_tags = set([tag for tag, aliases in JOB_TAGS['type'].items()
                         for alias in aliases if alias in (job['name'] + job_requirements).lower()])
        tech_tags = set([tag for tag, aliases in JOB_TAGS['tech'].items()
                         for alias in aliases if alias in (job['name'] + job_requirements).lower()])
        return {
            'name': job['name'],
            'employer': job['employer']['name'],
            'employer_logo': job['employer']['logo_urls']['original'] if job['employer'][
                                                                             'logo_urls'] is not None else '/static/nophoto.png',
            'tags': {'type': list(type_tags), 'tech': list(tech_tags), 'city': job['area']['name']},
            # back to list to make JSON serialization easier
            'url': job['alternate_url'],
            'date': job['published_at'][:10],
        }

    @staticmethod
    def without_degree(jobs: list):
        no_degree_jobs = []
        avoid = ['высшее', 'образование', 'вуз', 'профильное', 'студент']
        for job in jobs:
            requirements = job['snippet']['requirement']
            try:
                requirements = requirements.lower()
                description = ''
                with request.urlopen(job['url']) as response:
                    description = json.loads(response.read())['description']
                if not any([r in requirements + description for r in avoid]):
                    no_degree_jobs.append(job)
            except AttributeError:
                # since not every job posting on hh.ru has requirements,
                # we can just skip ones without them
                pass
        return no_degree_jobs

    @staticmethod
    def prepare_jobs(jobs: list):
        prepared_jobs = []
        for job in jobs:
            # get a set of tags that job name may contain. (we use set to exclude repetitive ones)
            type_tags = set([tag for tag, aliases in JOB_TAGS['type'].items()   # None to str if None
                             for alias in aliases if alias in (job['name'] + str(job['snippet']['requirement'])).lower()])
            tech_tags = set([tag for tag, aliases in JOB_TAGS['tech'].items()
                             for alias in aliases if alias in (job['name'] + str(job['snippet']['requirement'])).lower()])
            prepared_jobs.append({
                'name': job['name'],
                'employer': job['employer']['name'],
                'employer_logo': job['employer']['logo_urls']['original'] if job['employer']['logo_urls'] is not None else '/static/nophoto.png',
                'tags': {'type': list(type_tags), 'tech': list(tech_tags), 'city': job['area']['name']},
                # back to list to make JSON serialization easier
                'url': job['alternate_url'],
                'date': job['published_at'][:10],
            })
        return prepared_jobs