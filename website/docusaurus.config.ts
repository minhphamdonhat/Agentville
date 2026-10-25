import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Agentville',
  tagline: 'A team of helpers for Claude that plans, checks and reports its work',
  favicon: 'img/favicon.svg',

  url: 'https://minhphamdonhat.github.io',
  baseUrl: '/Agentville/',
  organizationName: 'minhphamdonhat',
  projectName: 'Agentville',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',

  i18n: {
    defaultLocale: 'en-GB',
    locales: ['en-GB'],
  },

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/minhphamdonhat/Agentville/tree/main/website/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Agentville',
      logo: {
        alt: 'Agentville',
        src: 'img/favicon.svg',
      },
      items: [
        {type: 'docSidebar', sidebarId: 'docs', position: 'left', label: 'Docs'},
        {to: '/docs/get-started', label: 'Get started', position: 'left'},
        {to: '/docs/faq', label: 'FAQ', position: 'left'},
        {
          href: 'https://github.com/minhphamdonhat/Agentville',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Introduction', to: '/docs/intro'},
            {label: 'Get started', to: '/docs/get-started'},
            {label: 'How it works', to: '/docs/how-it-works'},
            {label: 'FAQ', to: '/docs/faq'},
          ],
        },
        {
          title: 'More',
          items: [
            {label: 'For technical users', to: '/docs/technical'},
            {label: 'GitHub', href: 'https://github.com/minhphamdonhat/Agentville'},
          ],
        },
      ],
      copyright: 'Agentville is released under the MIT licence. Built with Docusaurus.',
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'powershell'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
