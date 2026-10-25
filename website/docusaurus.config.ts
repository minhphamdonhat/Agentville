import type {PrismTheme} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// Press & Paper code colours: ink and brick on newsprint, each at 4.5:1 or more.
const pressPaperCode: PrismTheme = {
  plain: {color: '#222020', backgroundColor: '#E8DCC4'},
  styles: [
    {types: ['comment', 'prolog', 'doctype', 'cdata'], style: {color: '#5C534B', fontStyle: 'italic'}},
    {types: ['punctuation', 'operator', 'entity', 'url'], style: {color: '#4A4440'}},
    {types: ['property', 'tag', 'boolean', 'number', 'constant', 'symbol', 'deleted'], style: {color: '#86221B'}},
    {types: ['selector', 'attr-name', 'string', 'char', 'builtin', 'inserted'], style: {color: '#3E5226'}},
    {types: ['atrule', 'attr-value', 'keyword'], style: {color: '#7A2E12'}},
    {types: ['function', 'class-name'], style: {color: '#222020', fontWeight: 'bold'}},
    {types: ['regex', 'important', 'variable'], style: {color: '#5E4530'}},
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
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },
  themes: ['@docusaurus/theme-mermaid'],

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
    // Press & Paper is a light edition only.
    colorMode: {
      defaultMode: 'light',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'neutral'},
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
      theme: pressPaperCode,
      additionalLanguages: ['bash', 'powershell'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
