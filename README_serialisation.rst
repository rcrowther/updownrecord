Why does UpDownRecord not use Django serialisation?

Because I didn't know about the feature before I wrote UpDownRecord, that's why.

Now I do know of serialisation, there may be a reassessment. However, there are differences,

Updown record primarily provides views to the activity. 
  This has nothing to do with how the recoreds are serialised.
Django serialisation is heavily concerned with capturing all the object witth it's related fields 
  Frankly, Updown record only cares about one model at a time.
Django serialisation cares about natural keys
  Updown record cares about the presence of keys
The feature set is differnt
 Updown can map keys, and hooks to normalise. Serialisation can only ignore an attribute or two.
 And I don't want the format.
  
