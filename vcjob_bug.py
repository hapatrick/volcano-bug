import argparse
import kubernetes
import time
import yaml


job_doc = """apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: job-{n:05}
  namespace: {namespace}
spec:
  maxRetry: 3
  minAvailable: 1
  queue: default
  schedulerName: volcano
  tasks:
    - maxRetry: 3
      minAvailable: 1
      name: "0"
      replicas: 1
      template:
        metadata:
          namespace: {namespace}
        spec:
          containers:
          - command:
            - sleep
            - "5"
            image: alpine
            name: job-0
            resources: {{}}
          restartPolicy: Never

"""

def kubernetes_connect(config_file=None):
    """
    Attempt to load config and establish a connection for the kubernetes client. 
    """
    if config_file is not None:
        kubernetes.config.load_kube_config(config_file)
        print('K8s client is configured with kubeconfig file {}'.format(config_file))
    else:
        try:
            kubernetes.config.load_incluster_config()  # cluster env vars
            print("K8s client is configured in cluster with service account.")
        except kubernetes.config.ConfigException as e1:
            kubernetes.config.load_kube_config()  # developer's config files
            print("K8s client is configured via default kubeconfig file.")


def create_job(api, i, namespace):
    job_yaml = job_doc.format(n=i, namespace=namespace)
    job_obj = yaml.safe_load(job_yaml)
    kubernetes.client.CustomObjectsApi(api).create_namespaced_custom_object('batch.volcano.sh',
                                                                            'v1alpha1',
                                                                            namespace,
                                                                            'jobs',
                                                                            job_obj)
    time.sleep(0.45)
    patch = {'metadata':
                 {'annotations':
                      {'foo': 'bar'}
                  }
             }
    kubernetes.client.CustomObjectsApi(api).patch_namespaced_custom_object('batch.volcano.sh',
                                                                            'v1alpha1',
                                                                            namespace,
                                                                            'jobs',
                                                                            f'job-{i:05}',
                                                                            patch)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Test')
    parser.add_argument('-n', type=str, required=False, default='default', help='The namespace')
    parser.add_argument('--config', type=str, required=False,
                        help='Optional kubeconfig file to use for connection. If not specified, will first try '
                        'loading in-cluster config, then try searching for default kubeconfig file.')

    args = parser.parse_args()

    kubernetes_connect(args.config)

    namespace = args.n

    N = 500

    print('Create vcjobs...')
    with kubernetes.client.ApiClient() as api:
        for i in range(N):
            create_job(api, i, namespace)

    # Wait for all to finish
    print('Wait for completion...')
    time.sleep(120)

    # Check status of all vcjobs
    print('Check status...')
    npending = 0
    ncompleted = 0
    nother = 0
    uncompleted_jobs = []
    with kubernetes.client.ApiClient() as api:
        for i in range(N):
            obj = kubernetes.client.CustomObjectsApi(api).get_namespaced_custom_object_status('batch.volcano.sh',
                                                                                    'v1alpha1',
                                                                                    namespace,
                                                                                    'jobs',
                                                                                    f'job-{i:05}')
            phase = obj.get('status', {}).get('state', {}).get('phase', '')
            if phase == 'Pending':
                npending += 1
                uncompleted_jobs.append(f'job-{i:05}')
            elif phase == 'Completed':
                ncompleted += 1
            else:
                nother += 1
                uncompleted_jobs.append(f'job-{i:05}')
    print(f'{N} jobs, completed = {ncompleted}, pending = {npending}, other = {nother}')
    if uncompleted_jobs:
        print('These jobs did not complete: ' + ','.join(uncompleted_jobs))

    # Delete all vcjobs
    if True:
        print('Delete vcjobs...')
        with kubernetes.client.ApiClient() as api:
            for i in range(N):
                job_name = f'job-{i:05}'
                if job_name not in uncompleted_jobs:
                    kubernetes.client.CustomObjectsApi(api).delete_namespaced_custom_object('batch.volcano.sh',
                                                                                            'v1alpha1',
                                                                                            namespace,
                                                                                            'jobs',
                                                                                            job_name)
    print('Done.')
