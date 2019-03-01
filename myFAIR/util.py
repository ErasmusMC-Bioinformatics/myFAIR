import json

class queries:
    @staticmethod
    def get_data_instance_query(
        username, password, 
        storage, 
        title, 
        filename,
        content_type, 
        userid, 
        projectid, 
        assayid, 
        description, 
        tags)

        data = { 
            'data': { 
                'type': 'data_files', 
                'attributes': { 
                    'title': title,
                    'description': description},
                    'tags': tags,
                    'license': 'CC-BY-4.0', 
                    'content_blobs': [ {
                        'original_filename': filename, 
                        'content_type': content_type}
                    }],
                    'policy': {
                        'access': 'download', 
                        'permissions': [{ 
                            'resource': { 
                                'id': str(projectid),
                                'type': 'projects'
                            },
                            'access': 'edit' 
                        } ] 
                    } 
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