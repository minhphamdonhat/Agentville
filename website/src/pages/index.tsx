import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import {Barcode, HandNote, Postmark, Stamp, WaxSeal} from '@site/src/components/Ephemera';
import styles from './index.module.css';

type Story = {
  number: string;
  kicker: string;
  title: string;
  body: string;
  link: {to: string; label: string};
};

const stories: Story[] = [
  {
    number: '01',
    kicker: 'Plan',
    title: 'It plans before it works',
    body: 'For anything bigger than a quick fix, Agentville talks the request through with you and writes a short plan before it changes anything.',
    link: {to: '/docs/how-it-works', label: 'How it works'},
  },
  {
    number: '02',
    kicker: 'Check',
    title: 'Its work is checked',
    body: 'A separate helper checks the result, and another reviews it, so you get evidence rather than a promise.',
    link: {to: '/docs/intro', label: 'What is Agentville?'},
  },
  {
    number: '03',
    kicker: 'Report',
    title: 'It tells you what is left',
    body: 'Every request ends with a plain report: what was done, what was checked and any decision that is still yours.',
    link: {to: '/docs/guides/following-along', label: 'Follow along'},
  },
];

const inside: {to: string; title: string; line: string}[] = [
  {to: '/docs/intro', title: 'Introduction', line: 'What Agentville does for you in Claude.'},
  {to: '/docs/get-started', title: 'Get started', line: 'Add the plugin and paste two lines.'},
  {to: '/docs/how-it-works', title: 'How it works', line: 'The six stages and the helpers.'},
  {to: '/docs/guides', title: 'Guides', line: 'Short guides for everyday use.'},
  {to: '/docs/technical', title: 'For technical users', line: 'Claude Code and the installer.'},
  {to: '/docs/faq', title: 'FAQ', line: 'Answers to common questions.'},
];

const steps: {number: string; title: string; body: string}[] = [
  {number: '01', title: 'Add the plugin', body: 'Add Agentville once, from the plugin settings in Claude.'},
  {number: '02', title: 'Paste two lines', body: 'Paste two lines into your Claude settings, so every chat uses it.'},
  {number: '03', title: 'Talk to Claude', body: 'Then talk to Claude as you always do.'},
];

const classifieds: {heading: string; body: string; link: {to: string; label: string}}[] = [
  {
    heading: 'Wanted: a clear request',
    body: 'Ask in a way that gets it right first time.',
    link: {to: '/docs/guides/good-requests', label: 'Write a good request'},
  },
  {
    heading: 'Keep it current',
    body: 'Update, pause or remove Agentville in Claude Chat and Cowork.',
    link: {to: '/docs/guides/updating', label: 'Keep Agentville up to date'},
  },
  {
    heading: 'Terminal users',
    body: 'Claude Code, the command-line installer and the release channels.',
    link: {to: '/docs/technical', label: 'For technical users'},
  },
  {
    heading: 'Free to use',
    body: 'Agentville is released under the MIT licence; the source is on GitHub.',
    link: {to: 'https://github.com/minhphamdonhat/Agentville', label: 'Agentville on GitHub'},
  },
];

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Agentville gives Claude a small team of helpers that plan, do, check and report your work.">
      <main className={styles.front}>
        <div className={styles.sheet}>
          <header className={styles.masthead}>
            <p className={styles.ear}>
              <span>Vol. 1 · No. 1</span>
              <span>A plugin for Claude</span>
            </p>
            <Heading as="h1" className={styles.nameplate}>
              Agentville
            </Heading>
            <p className={`${styles.ear} ${styles.earRight}`}>
              <span>Price: Free</span>
              <span>MIT licence</span>
            </p>
          </header>

          <p className={styles.dateline}>
            First edition, 2026 · For Claude Chat, Cowork and Claude Code · Plans, checks and reports its work
          </p>

          <ul className={styles.ticker} aria-label="Agentville at a glance">
            <li>
              Stages <span className={styles.score}>6</span>
            </li>
            <li>
              Helpers <span className={styles.score}>5</span>
            </li>
            <li>
              Release channels <span className={styles.score}>3</span>
            </li>
            <li>
              Price <span className={styles.score}>Free</span>
            </li>
          </ul>

          <section className={styles.above} aria-labelledby="lead-headline">
            <div className={styles.leadBox}>
              <p className={styles.kicker}>Front page</p>
              <Heading as="h2" id="lead-headline" className={styles.leadHeadline}>
                A small team of helpers for Claude that plans, does, checks and reports your work
              </Heading>
              <p className={styles.standfirst}>
                Agentville is a free add-on, called a plugin, for Claude. You add it once, paste two lines into
                your Claude settings, and then you talk to Claude as you always do.
              </p>
              <Link className={styles.cta} to="/docs/get-started">
                Get started{'\u00a0'}<span aria-hidden="true">→</span>
              </Link>
            </div>
            <div className={styles.openerMargin}>
              <Stamp className={`${styles.ornament} ${styles.stamp}`} />
              <Postmark className={`${styles.ornament} ${styles.postmark}`} />
            </div>
          </section>

          <section className={styles.stories} aria-label="Stories">
            {stories.map((story, index) => (
              <article
                key={story.number}
                className={index === 0 ? `${styles.story} ${styles.leadStory}` : styles.story}>
                <p className={styles.sectionLabel}>
                  <span className={styles.sectionNumber}>{story.number}</span> — {story.kicker}
                </p>
                <Heading as="h3" className={index === 0 ? styles.leadStoryTitle : styles.storyTitle}>
                  {story.title}
                </Heading>
                <p className={index === 0 ? styles.lede : undefined}>{story.body}</p>
                {index === 0 && (
                  <p>
                    When you ask for something, Agentville first decides how much care the request needs. A quick
                    question gets a quick answer, with no extra steps. A small, clear task goes straight to the work.
                    A large or unclear task starts with a short conversation, so Claude understands what you want
                    before it builds anything.
                  </p>
                )}
                <Link className={styles.arrowLink} to={story.link.to}>
                  {story.link.label}{'\u00a0'}<span aria-hidden="true">→</span>
                </Link>
              </article>
            ))}
            <aside className={styles.sidebarBox} aria-labelledby="inside-heading">
              <Heading as="h3" id="inside-heading" className={styles.boxHeading}>
                Inside this edition
              </Heading>
              <ol className={styles.insideList}>
                {inside.map((item) => (
                  <li key={item.to}>
                    <Link to={item.to}>{item.title}</Link>
                    <span className={styles.insideLine}>{item.line}</span>
                  </li>
                ))}
              </ol>
            </aside>
          </section>

          <section aria-labelledby="steps-heading">
            <Heading as="h2" id="steps-heading" className={styles.boxedHead}>
              Three steps
            </Heading>
            <ol className={styles.stepList} role="list">
              {steps.map((step) => (
                <li key={step.number}>
                  <span className={styles.stepNumber} aria-hidden="true">
                    {step.number}
                  </span>
                  <span className={styles.stepTitle}>{step.title}</span>
                  <span className={styles.stepBody}>{step.body}</span>
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="classifieds-heading">
            <Heading as="h2" id="classifieds-heading" className={styles.boxedHead}>
              Classifieds
            </Heading>
            <div className={styles.classifieds}>
              {classifieds.map((ad) => (
                <div key={ad.heading} className={styles.classified}>
                  <Heading as="h3" className={styles.classifiedHeading}>
                    {ad.heading}
                  </Heading>
                  <p>{ad.body}</p>
                  <Link className={styles.arrowLink} to={ad.link.to}>
                    {ad.link.label}{'\u00a0'}<span aria-hidden="true">→</span>
                  </Link>
                </div>
              ))}
              <div className={styles.noteCell}>
                <p className={styles.noteText}>
                  Add only <Link to="/docs/get-started">the Stable version</Link>: the three versions clash with
                  each other, so add just one.
                </p>
                <HandNote className={`${styles.ornament} ${styles.note}`} lines={['Stable only,', 'just one!']} />
              </div>
            </div>
          </section>

          <div className={styles.folio}>
            <span>Page 1</span>
            <span>Agentville · The front page</span>
            <span>minhphamdonhat.github.io/Agentville</span>
            <span className={styles.folioOrnaments}>
              <Barcode className={styles.barcode} />
              <WaxSeal className={`${styles.ornament} ${styles.seal}`} />
            </span>
          </div>
        </div>
      </main>
    </Layout>
  );
}
