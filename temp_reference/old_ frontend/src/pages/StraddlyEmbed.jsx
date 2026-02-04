import React from 'react';
import PropTypes from 'prop-types';

// Map friendly route keys to actual static files under public/STRADDLY
const STRADDLY_PAGES = {
  watchlist: '/STRADDLY/Watchlist.html',
  options: '/STRADDLY/Options.html',
  orders: '/STRADDLY/Orders.html',
  ledger: '/STRADDLY/ledger.html',
  payouts: '/STRADDLY/payouts.html',
  profile: '/STRADDLY/Profile.html',
  positions: '/STRADDLY/Positions.html',
  baskets: '/STRADDLY/Baskets.html',
  mis: '/STRADDLY/MIS Positions.html',
  normalpositions: '/STRADDLY/Normal Positions.html',
  userwise: '/STRADDLY/P userwise.html',
  straddle: '/STRADDLY/Straddle.html'
};

// A simple full-viewport iframe embed for static Straddly pages saved in public/STRADDLY
const StraddlyEmbed = ({ pageKey }) => {
  const src = STRADDLY_PAGES[pageKey];

  if (!src) {
    return (
      <div className="flex items-center justify-center h-screen text-sm text-gray-600">
        Unknown Straddly page: {pageKey}
      </div>
    );
  }

  return (
    <div className="w-full h-screen bg-gray-50">
      <iframe
        title={`Straddly - ${pageKey}`}
        src={src}
        className="w-full h-full border-0"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
      />
    </div>
  );
};

StraddlyEmbed.propTypes = {
  pageKey: PropTypes.string.isRequired
};

export default StraddlyEmbed;
