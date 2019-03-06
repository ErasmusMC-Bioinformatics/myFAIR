import json

class queries:
    @staticmethod
    def get_data_instance_query(
        username, password, storage, 
        title, 
        filename,
        content_type, 
        userid, 
        projectid, 
        assayid, 
        description, 
        tags):

        data = { 
            'data': { 
                'type': 'data_files', 
                'attributes': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'license': 'CC-BY-4.0', 
                    'content_blobs': [{
                        'original_filename': filename, 
                        'content_type': content_type
                    }]
                },
                'policy': {
                    'access': 'download', 
                    'permissions': [{ 
                        'resource': { 
                            'id': str(projectid),
                            'type': 'projects'
                        },
                        'access': 'edit' 
                    }]
                },
                'relationships': {
                    'creators': { 
                        'data': [ {
                            'id': str(userid),
                            'type': 'people' 
                        }] 
                    },
                    'projects': { 
                        'data': [{ 
                            'id': str(projectid),
                            'type': 'projects' 
                        } ] 
                    }, 
                    'assays': { 
                        'data': [{ 
                            'id': str(assayid), 
                            'type': 'assays' 
                        } ] 
                    } 
                }
            }
        }
        return "curl " +
        "-u {username}:{password} -X POST '{storage}/data_files' " +
        "-H 'accept: application/json' -H 'Content-Type: application/json' " +
        "-d '{data}' ".format(
            username=username,
            password=password,
            storage=storage,
            data=json.dumps(data)
        )

    @staticmethod
    def get_study_creation_query(
        username, password, server
        title,
        description,
        userid,
        projectid,
        investigationid):

        data = {
            'type': 'studies',
            'attributes': {
                'title': title,
                'description': description,
                'person_responsible_id': str(userid),
                'policy': {
                    'access': 'download',
                    'permissions': [{
                        'resource': {
                            'id': str(projectid),
                            'type': 'projects'
                        },
                        'access': 'view'
                    }]
                }
            },
            'relationships': {
                'investigation': {
                    'data': {
                        'id': str(investigationid),
                        'type': 'investigations'
                    }
                },
                'creators': {
                    'data': [{
                        'id': str(userid),
                        'type': 'people'
                    }]
                }
            }
        }
        return "curl " +
            "-u {username}:{password} -X POST '{server}/studies' " +
            "-H 'accept: application/json' -H 'Content-Type: application/json' " +
            "-d '{data}' ".format(
            username=username,
            password=password,
            server=server,
            data=json.dumps(data)
        )

    @staticmethod
    def get_assay_creation_query(
        username, password,
        title,
        assay_type,
        technology_type,
        description,
        projectid,
        studyid
        userid):
        data = {
            'data': {
                'type': 'assays',
                'attributes': {
                    'title': title,
                    'assay_class': {
                        'key': 'EXP'
                    },
                    'assay_type': {
                        'uri': assay_type
                    },
                    'technology_type': {
                        'uri': technology_type
                    },
                    'description': description,
                    'policy': {
                        'access': 'download',
                        'permissions': [{
                            'resource': {
                                'id': str(projectid),
                                'type': 'projects' 
                            },
                            'access': 'view'
                        }]
                    }
                }, 
                'relationships': {
                    'study': {
                        'data': {
                            'id': str(studyid),
                            'type': 'studies'
                        }
                    },
                    'creators': {
                        'data': [{
                            'id': str(userid),
                            'type': 'people'
                        }]
                    }
                }
            }
        }
        return "curl " +
            "-u {username}:{password} -X POST '{server}/assays' " +
            "-H 'accept: application/json' -H 'Content-Type: application/json' " +
            "-d '{data}' ".format(
            username=username,
            password=password,
            server=server,
            data=json.dumps(data)
        )