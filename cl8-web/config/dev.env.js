'use strict'
const merge = require('webpack-merge')
const prodEnv = require('./prod.env')

module.exports = merge(prodEnv, {
  NODE_ENV: process.env.NODE_ENV_DEV,

  FIREBASE_APIKEY: `'${process.env.FIREBASE_APIKEY_DEV}'`,
  FIREBASE_AUTHDOMAIN: `'${process.env.FIREBASE_AUTHDOMAIN_DEV}'`,
  FIREBASE_DATABASEURL: `'${process.env.FIREBASE_DATABASEURL_DEV}'`,
  FIREBASE_PROJECTID: `'${process.env.FIREBASE_PROJECTID_DEV}'`,
  FIREBASE_STORAGEBUCKET: `'${process.env.FIREBASE_STORAGEBUCKET_DEV}'`,
  FIREBASE_MESSAGINGSENDERID: `'${process.env.FIREBASE_MESSAGINGSENDERID_DEV}'`,
  FIREBASE_FUNCTIONSURL: `'${process.env.FIREBASE_FUNCTIONSURL_DEV}'`,
  GOOGLE_ANALYTICS_UA: `'${process.env.GOOGLE_ANALYTICS_UA_DEV}'`
})
