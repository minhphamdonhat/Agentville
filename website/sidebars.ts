import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    'intro',
    'get-started',
    'how-it-works',
    {
      type: 'category',
      label: 'Guides',
      link: {type: 'doc', id: 'guides/index'},
      items: ['guides/good-requests', 'guides/following-along', 'guides/updating'],
    },
    {
      type: 'category',
      label: 'For technical users',
      link: {type: 'doc', id: 'technical/index'},
      items: ['technical/claude-code', 'technical/command-line', 'technical/channels'],
    },
    'faq',
  ],
};

export default sidebars;
