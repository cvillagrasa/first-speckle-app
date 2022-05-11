from dataclasses import dataclass
import pandas as pd
import plotly.express as px
import streamlit as st
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_account_from_token
from misc import commit_url, list_to_markdown


@dataclass
class SpeckleConnection:
    server: str = 'speckle.xyz'
    token: str = ''
    client: ... = None
    account: ... = None

    def __call__(self):
        self.client = SpeckleClient(host=self.server)
        self.account = get_account_from_token(self.token, self.server)
        self.client.authenticate_with_account(self.account)

    @property
    def streams(self):
        return self.client.stream.list()

    def branches_from_stream(self, stream_id):
        return self.client.branch.list(stream_id)

    def commits_from_stream(self, stream_id, limit=100):
        return self.client.commit.list(stream_id, limit=limit)

    def stream_by_name(self, name):
        return self.client.stream.search(name)[0]


@dataclass
class SpeckleWebApp:
    page_title_tab: str = 'Speckle Stream Activity'
    page_title_header: str = 'Speckle Stream Activity App 📈'
    page_icon: str = '📊'
    server: str = 'speckle.xyz'
    token: str = None
    selected_stream_name: str = None
    selected_stream: ... = None
    branches: list = None
    commits: list = None

    def __post_init__(self):
        self.container_titles = ['header', 'inputs', 'viewer', 'report', 'graphs']
        self.setup_page()
        self.connection = SpeckleConnection()
        self.containers = {title: st.container() for title in self.container_titles}
        self.setup_header()
        self.setup_inputs()
        self.setup_viewer()
        self.setup_report()
        self.setup_graphs()

    def __getitem__(self, item):
        return self.containers[item] if item in self.containers else None

    def set_login_info(self, server, token):
        self.server, self.token = server, token
        self.connection.server, self.connection.token = server, token

    def setup_page(self):
        st.set_page_config(page_title=self.page_title_tab, page_icon=self.page_icon)

    def setup_header(self):
        with self['header']:
            st.title(self.page_title_header)
        with self['header'].expander('About this app 🔽', expanded=True):
            st.markdown(
                "This is a simple Streamlit web app which interacts with the Speckle API"
            )

    def setup_inputs(self):
        with self['inputs']:
            st.subheader('Inputs')
            cols = st.columns([1, 3])
            server = cols[0].text_input('Server URL', 'speckle.xyz', help='Speckle server to connect.')
            token = cols[1].text_input(
                'Speckle token', self.token,
                help="""If you don't know how to get your token, take a look at 
                <https://speckle.guide/dev/tokens.html>👈"""
            )
            self.set_login_info(server=server, token=token)
            self.connection()
            stream_names = [s.name for s in self.connection.streams]
            self.selected_stream_name = st.selectbox(
                label='Select your stream', options=stream_names, help='Select your stream from the dropdown'
            )
            self.selected_stream = self.connection.stream_by_name(self.selected_stream_name)
            self.branches = self.connection.branches_from_stream(self.selected_stream.id)
            self.commits = self.connection.commits_from_stream(self.selected_stream.id)

    def setup_viewer(self):
        with self['viewer']:
            st.subheader('Latest Commit 👇')
            src = commit_url(self.selected_stream, self.commits[0])
            st.components.v1.iframe(src=src, height=400)

    def setup_report(self):
        with self['report']:
            st.subheader('Statistics')
            cols = st.columns(4)

            num_branches = self.selected_stream.branches.totalCount
            cols[0].metric(label='Number of branches', value=num_branches)
            branch_names = [branch.name for branch in self.branches]
            cols[0].markdown(list_to_markdown(branch_names))

            num_commits = len(self.commits)
            cols[1].metric(label='Number of commits', value=num_commits)

            connector_list = [commit.sourceApplication for commit in self.commits]
            connector_dict = dict.fromkeys(connector_list)  # duplicates removed
            connector_list = list(connector_dict)
            num_connectors = len(connector_dict)
            cols[2].metric(label='Number of connectors', value=num_connectors)
            cols[2].markdown(list_to_markdown(connector_list))

            num_contributors = len(self.selected_stream.collaborators)
            contributors = [collaborator.name for collaborator in self.selected_stream.collaborators]
            contributors = list(dict.fromkeys(contributors))  # duplicates removed
            cols[3].metric(label='Number of contributors', value=num_contributors)
            cols[3].markdown(list_to_markdown(contributors))

    def setup_graphs(self):
        with self['graphs']:
            st.subheader('Graphs')
            cols = st.columns([2, 1, 1])

            branch_counts = pd.DataFrame(
                [[branch.name, branch.commits.totalCount] for branch in self.branches],
                columns=['branch', 'num_commits']
            )
            branch_graph = px.bar(
                branch_counts, x='branch', y='num_commits', color='branch', labels={'branch': '', 'num_commits': ''}
            )
            branch_graph.update_layout(showlegend=False, margin={'l': 1, 'r': 1, 't': 1, 'b': 1}, height=220)
            cols[0].plotly_chart(branch_graph, use_container_width=True)

            commits_df = pd.DataFrame([commit.dict() for commit in self.commits])
            apps_df = commits_df['sourceApplication']
            apps_df = apps_df.value_counts().reset_index()
            apps_df.columns = ['app', 'count']
            commit_graph = px.pie(apps_df, names='app', values='count', hole=0.5)
            commit_graph.update_layout(showlegend=False, margin={'l': 1, 'r': 1, 't': 1, 'b': 1}, height=200)
            cols[1].plotly_chart(commit_graph, use_container_width=True)

            authors_df = commits_df['authorName'].value_counts().reset_index()
            authors_df.columns = ['author', 'count']
            authors_graph = px.pie(authors_df, names='author', values='count', hole=0.5)
            authors_graph.update_layout(showlegend=False, margin={'l': 1, 'r': 1, 't': 1, 'b': 1}, height=200,
                                        yaxis_scaleanchor='x')
            cols[2].plotly_chart(authors_graph, use_container_width=True)

            st.subheader('Commit Activity Timeline 🕒')
            cdate = pd.to_datetime(commits_df['createdAt']).dt.date.value_counts().reset_index().sort_values('index')
            null_days = pd.date_range(start=cdate['index'].min(), end=cdate['index'].max())
            cdate = cdate.set_index('index').reindex(null_days, fill_value=0)
            cdate = cdate.reset_index()
            cdate.columns = ['date', 'count']
            cdate['date'] = pd.to_datetime(cdate['date']).dt.date
            timeline_graph = px.line(cdate, x='date', y='count', markers=True)
            st.plotly_chart(timeline_graph, use_container_width=True)
