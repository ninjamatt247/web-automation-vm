import { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

import Logo from '@/components/layout/logo';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: <Logo className="text-lg" iconClassName="w-6" noLink />,
  },
};
