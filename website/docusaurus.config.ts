import type {PrismTheme} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// Press & Paper code colours: ink, brick and green on the grey panel, each at 4.5:1 or more.
const pressPaperCode: PrismTheme = {
  plain: {color: '#222020', backgroundColor: '#F4F3F0'},
  styles: [
    {types: ['comment', 'prolog', 'doctype', 'cdata'], style: {color: '#5A5856', fontStyle: 'italic'}},
    {types: ['punctuation', 'operator', 'entity', 'url'], style: {color: '#4A4846'}},
    {types: ['property', 'tag', 'boolean', 'number', 'constant', 'symbol', 'deleted'], style: {color: '#A32A22'}},
    {types: ['selector', 'attr-name', 'string', 'char', 'builtin', 'inserted'], style: {color: '#2F5D3A'}},
    {types: ['atrule', 'attr-value', 'keyword'], style: {color: '#86221B'}},
    {types: ['function', 'class-name'], style: {color: '#222020', fontWeight: 'bold'}},
    {types: ['regex', 'important', 'variable'], style: {color: '#6B4F35'}},
  ],
};

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
    // Press & Paper is a light edition only: a white sheet on a lavender-grey mat.
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
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
      style: 'light',
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
      theme: pressPaperCode,
      additionalLanguages: ['bash', 'powershell'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
